const TTL_MS = 60 * 60 * 1000
const TICK_MS = 30 * 1000

let lastAt = null
let now = 0
let ticking = null

function leftColor(minutes) {
  if (minutes > 20) return 'green'
  if (minutes > 5) return 'yellow'
  return 'red'
}

export function register(on) {
  on('turn.step', async function* ($, e, next) {
    const result = yield* next(e)
    if (!e.agentId && result.usage) {
      lastAt = now = await $.clock.now()
      ticking ??= $.clock.every(TICK_MS, async () => {
        now = await $.clock.now()
        $.ui.invalidate('ui.render')
      })
      $.ui.invalidate('ui.render')
    }
    return result
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const theirs = await next(e)
    const { Box, Text } = $.ui.resolve(e)
    const dim = (text) => Text({ dimColor: true, children: [text] })
    const withTheirs = (line) => (theirs ? Box({ flexDirection: 'column', children: [line, theirs] }) : line)

    if (lastAt === null) return withTheirs(dim('cache · waiting for first request'))

    const width = e.props.bodyColumns >= 110 ? 24 : 12
    const leftMs = Math.max(0, TTL_MS - (now - lastAt))

    if (leftMs === 0) {
      return withTheirs(
        Box({
          flexDirection: 'row',
          children: [
            dim('cache  ' + '░'.repeat(width) + '  '),
            Text({ color: 'red', children: ['expired'] }),
            dim(' · next request rewrites it'),
          ],
        }),
      )
    }

    const minutes = Math.ceil(leftMs / 60000)
    const full = Math.ceil((leftMs / TTL_MS) * width)
    const color = leftColor(minutes)
    return withTheirs(
      Box({
        flexDirection: 'row',
        children: [
          dim('cache  '),
          Text({ color, children: ['█'.repeat(full)] }),
          dim('░'.repeat(width - full) + '  '),
          Text({ color, children: [minutes + ' min left'] }),
          dim(' · ' + (60 - minutes) + " min since last request"),
        ],
      }),
    )
  })
}
