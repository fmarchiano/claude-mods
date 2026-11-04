import { test, expect } from 'claude-code/testing'
import { cacheBar, contextBar, isHandoffDue } from './register.ts'

test('context bar fills on a 300k scale with the marker at 150k', () => {
  expect(contextBar(40_000)).toBe('🟢 ctx ██░░░░░░░░|░░░░░░░░░░ 40k/150k')
  expect(contextBar(120_000)).toBe('🟡 ctx ████████░░|░░░░░░░░░░ 120k/150k')
  expect(contextBar(290_000)).toBe('🔴 ctx ██████████|█████████░ 290k/150k')
  expect(contextBar(900_000)).toBe('🔴 ctx ██████████|██████████ 900k/150k')
})

test('cache bar counts down and reads expired at zero', () => {
  const hour = 60 * 60_000
  expect(cacheBar(hour, hour)).toBe('cache ██████████ 60:00')
  expect(cacheBar(30 * 60_000, hour)).toBe('cache █████░░░░░ 30:00')
  expect(cacheBar(61_000, 5 * 60_000)).toBe('cache ███░░░░░░░ 1:01')
  expect(cacheBar(0, hour)).toBe('cache ░░░░░░░░░░ expired')
})

test('handoff is due only in the last five minutes of a warm cache', () => {
  expect(isHandoffDue(10 * 60_000)).toBe(false)
  expect(isHandoffDue(5 * 60_000)).toBe(true)
  expect(isHandoffDue(1_000)).toBe(true)
  expect(isHandoffDue(0)).toBe(false)
})
