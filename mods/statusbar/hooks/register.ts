import type { EngineInterface, Register } from 'claude-code'

const SCALE = 300_000
const LIMIT = 150_000
const CTX_WIDTH = 20
const CACHE_WIDTH = 10
const TTL_MS = 60 * 60_000
// How long before the cache lapses the handoff fires, so it is written on a warm cache
const HANDOFF_LEAD_MS = 5 * 60_000

export const contextBar = (tokens: number): string => {
  const filled = Math.min(CTX_WIDTH, Math.floor((tokens * CTX_WIDTH) / SCALE))
  const mark = Math.floor((LIMIT * CTX_WIDTH) / SCALE)
  let bar = ''
  for (let i = 0; i < CTX_WIDTH; i++) {
    if (i === mark) bar += '|'
    bar += i < filled ? '█' : '░'
  }
  const dot = tokens >= LIMIT ? '🔴' : tokens >= 100_000 ? '🟡' : '🟢'
  return `${dot} ctx ${bar} ${Math.floor(tokens / 1000)}k/150k`
}

export const cacheBar = (leftMs: number, ttlMs: number): string => {
  if (leftMs <= 0) return `cache ${'░'.repeat(CACHE_WIDTH)} expired`
  const left = Math.ceil(leftMs / 1000)
  const filled = Math.ceil((leftMs * CACHE_WIDTH) / ttlMs)
  const time = `${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')}`
  return `cache ${'█'.repeat(filled)}${'░'.repeat(CACHE_WIDTH - filled)} ${time}`
}

export const isHandoffDue = (leftMs: number, tokens: number): boolean =>
  leftMs > 0 && leftMs <= HANDOFF_LEAD_MS && tokens >= 30_000

export const handoffPrompt = (path: string): string =>
  `The prompt cache is about to expire. Write a handoff document summarising this conversation so a fresh session can continue the work. ` +
  `Include a "suggested skills" section, reference existing artifacts by path instead of repeating them, and redact secrets and personal data. ` +
  `Save it at exactly ${path} and reply with that path only.`

let lastResponseAt: number | undefined
let model = ''
let effort = ''
let isBusy = false
let handoffPath: string | undefined
let handoffFired = false
let lastContextTokens = 0

async function refresh($: EngineInterface) {
  const { context } = await $.session.usage()
  lastContextTokens = context.tokens ?? 0
  const parts = [model || (await $.session.model())]
  if (effort) parts.push(`effort:${effort}`)
  if (lastContextTokens) parts.push(contextBar(lastContextTokens))
  if (lastResponseAt !== undefined) {
    const left = lastResponseAt + TTL_MS - (await $.clock.now())
    if (handoffPath) {
      parts.push('handoff: writing…')
    } else {
      parts.push(cacheBar(left, TTL_MS))
    }
    if (!handoffFired && !isBusy && !handoffPath && isHandoffDue(left, lastContextTokens)) {
      await startHandoff($)
    }
  }
  $.ui.status(parts.join(' | '))
}

async function startHandoff($: EngineInterface) {
  handoffFired = true
  handoffPath = `/tmp/claude-handoff-${await $.session.id()}.md`
  try {
    await $.prompt.submit({ text: handoffPrompt(handoffPath) })
  } catch {
    await $.prompt.fill({ text: handoffPrompt(handoffPath), mode: 'replace' })
  }
}

async function finishHandoff($: EngineInterface, path: string) {
  handoffPath = undefined
  const isWritten = await $.fs.stat(path).then(() => true, () => false)
  if (!isWritten) {
    await $.ui.notify(`Cache handoff ran, but ${path} was not written. The session was kept.`, { title: 'statusbar' })
    return
  }
  const cleared = await $.command.run({ command: 'clear' }).then(() => true, () => false)
  if (cleared) lastResponseAt = undefined
  await $.prompt.fill({ text: `Read the handoff at ${path} and continue from it.`, mode: 'replace' })
  await $.ui.notify(
    cleared
      ? `Handoff saved to ${path}. Session cleared; press Enter to continue in a fresh one (/resume brings the old one back).`
      : `Handoff saved to ${path}. Run /clear, then press Enter on the filled prompt.`,
    { title: 'statusbar' },
  )
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const result = await next(e)
    $.clock.every(1000, () => refresh($))
    return result
  })

  on('session.end', async ($, e, next) => {
    lastResponseAt = undefined
    return next(e)
  })

  on('prompt.submit', async ($, e, next) => {
    // User spoke — re-arm for the next idle stretch
    if (e.origin?.kind === 'composer' || e.origin?.kind === 'bridge') handoffFired = false
    return next(e)
  })

  on('turn.start', async ($, e, next) => {
    if (e.agentId === undefined) isBusy = true
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId === undefined) {
      isBusy = false
      if (handoffPath !== undefined) await finishHandoff($, handoffPath)
    }
    return result
  })

  on('turn.step', async function* ($, e, next) {
    const result = yield* next(e)
    if (e.agentId === undefined && result.usage !== null) {
      lastResponseAt = await $.clock.now()
      model = result.usage.model
      effort = e.effort === undefined ? '' : String(e.effort)
    }
    return result
  })
}
