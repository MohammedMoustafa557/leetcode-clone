// Run with: npm run test:unit  (node --test, Node >= 22.18 strips TS types natively)
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createSafeStorage } from '../src/lib/storage.ts'

class FakeStorage {
  data = new Map<string, string>()
  get length() { return this.data.size }
  clear() { this.data.clear() }
  key(i: number) { return [...this.data.keys()][i] ?? null }
  getItem(k: string) { return this.data.get(k) ?? null }
  setItem(k: string, v: string) { this.data.set(k, String(v)) }
  removeItem(k: string) { this.data.delete(k) }
}

test('uses real storage when available', () => {
  const fake = new FakeStorage()
  const s = createSafeStorage(() => fake as unknown as Storage)
  s.set('a', '1')
  assert.equal(fake.getItem('a'), '1')
  assert.equal(s.get('a'), '1')
  assert.equal(s.isMemoryOnly, false)
  s.remove('a')
  assert.equal(s.get('a'), null)
})

test('does not throw when accessing storage throws SecurityError (sandboxed iframe)', () => {
  const s = createSafeStorage(() => {
    throw new DOMException("Failed to read the 'localStorage' property from 'Window'", 'SecurityError')
  })
  assert.doesNotThrow(() => s.get('x'))
  assert.equal(s.get('x'), null)
  s.set('x', 'draft')
  assert.equal(s.get('x'), 'draft') // in-memory fallback
  assert.equal(s.isMemoryOnly, true)
  s.remove('x')
  assert.equal(s.get('x'), null)
})

test('survives setItem throwing (quota exceeded) and getItem throwing later', () => {
  const fake = new FakeStorage()
  const s = createSafeStorage(() => fake as unknown as Storage)
  s.get('probe-first')
  fake.setItem = () => { throw new DOMException('full', 'QuotaExceededError') }
  assert.doesNotThrow(() => s.set('k', 'v'))
  fake.getItem = () => { throw new DOMException('blocked', 'SecurityError') }
  assert.equal(s.get('k'), 'v')
})

test('undefined storage (SSR / old browsers) falls back to memory', () => {
  const s = createSafeStorage(() => undefined)
  s.set('t', 'dark')
  assert.equal(s.get('t'), 'dark')
})
