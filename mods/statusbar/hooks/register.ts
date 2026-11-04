import type { EngineInterface, Register } from 'claude-code'

const SCALE = 300_000
const LIMIT = 150_000
const CTX_WIDTH = 20
const CACHE_WIDTH = 10

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

let ttlMs = 60 * 60_000
let lastResponseAt: number | undefined
let model = ''
let effort = ''

async function refresh($: EngineInterface) {
  const { context } = await $.session.usage()
  const parts = [model || (await $.session.model())]
  if (effort) parts.push(`effort:${effort}`)
  if (context.tokens !== undefined) parts.push(contextBar(context.tokens))
  if (lastResponseAt !== undefined) parts.push(cacheBar(lastResponseAt + ttlMs - (await $.clock.now()), ttlMs))
  $.ui.status(parts.join(' | '))
}

export const register: Register = (on, options) => {
  ttlMs = options.cacheTtl === '5m' ? 5 * 60_000 : 60 * 60_000

  on('session.start', async ($, e, next) => {
    const result = await next(e)
    $.clock.every(1000, () => refresh($))
    return result
  })

  // Main-thread responses only: a subagent's request does not touch the main cache entry
  on('turn.step', async function* ($, e, next) {
    const result = yield* next(e)
    if (e.agentId === undefined && result.usage !== null) {
      lastResponseAt = await $.clock.now()
      model = result.usage.model
      effort = e.effort === undefined ? '' : String(e.effort)
      await refresh($)
    }
    return result
  })
}
