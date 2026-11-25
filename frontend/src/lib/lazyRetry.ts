import { lazy, type ComponentType } from 'react'

/** React.lazy that retries a failed chunk download (flaky networks, server restarts) before giving up. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function lazyRetry<T extends ComponentType<any>>(load: () => Promise<{ default: T }>, retries = 3, delayMs = 800) {
  return lazy(async () => {
    let lastError: unknown
    for (let i = 0; i <= retries; i++) {
      try {
        return await load()
      } catch (e) {
        lastError = e
        await new Promise((r) => setTimeout(r, delayMs * (i + 1)))
      }
    }
    throw lastError
  })
}
