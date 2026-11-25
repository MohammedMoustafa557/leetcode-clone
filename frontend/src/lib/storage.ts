/**
 * Safe wrapper around Web Storage.
 *
 * Accessing `window.localStorage` can THROW (not just return null) in sandboxed
 * iframes, some privacy modes and when storage is disabled
 * ("SecurityError: Failed to read the 'localStorage' property").
 * Every read/write in the app goes through here, so the UI keeps working with an
 * in-memory fallback instead of crashing.
 */

export interface SafeStorage {
  get(key: string): string | null
  set(key: string, value: string): void
  remove(key: string): void
  /** true when values are only kept in memory for this tab */
  readonly isMemoryOnly: boolean
}

type StorageGetter = () => Storage | undefined

export function createSafeStorage(getStorage: StorageGetter): SafeStorage {
  const memory = new Map<string, string>()
  let backend: Storage | null | undefined // undefined = not probed yet

  const resolve = (): Storage | null => {
    if (backend !== undefined) return backend
    try {
      const s = getStorage()
      if (!s) throw new Error('no storage')
      const probe = '__codearena_probe__'
      s.setItem(probe, '1')
      s.removeItem(probe)
      backend = s
    } catch {
      backend = null
    }
    return backend
  }

  return {
    get(key) {
      const s = resolve()
      if (s) {
        try {
          return s.getItem(key)
        } catch {
          /* fall through to memory */
        }
      }
      return memory.get(key) ?? null
    },
    set(key, value) {
      memory.set(key, value)
      const s = resolve()
      if (!s) return
      try {
        s.setItem(key, value)
      } catch {
        /* quota exceeded or blocked: memory copy is kept */
      }
    },
    remove(key) {
      memory.delete(key)
      const s = resolve()
      if (!s) return
      try {
        s.removeItem(key)
      } catch {
        /* ignore */
      }
    },
    get isMemoryOnly() {
      return resolve() === null
    },
  }
}

export const local = createSafeStorage(() => window.localStorage)
export const session = createSafeStorage(() => window.sessionStorage)
