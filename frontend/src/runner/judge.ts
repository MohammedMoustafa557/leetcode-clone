import type { JudgeResult, WorkerRequest, WorkerResponse } from './protocol'

type Pending = { resolve: (v: unknown) => void; reject: (e: Error) => void; timer?: number }
type DistributiveOmit<T, K extends keyof never> = T extends unknown ? Omit<T, K> : never

export const RUN_CASES = 3
export const TIME_LIMIT_MS = 10_000
export const HEAVY_TIME_LIMIT_MS = 30_000
const BOOT_TIMEOUT_MS = 90_000

class Judge {
  private worker: Worker | null = null
  private ready: Promise<void> | null = null
  private nextId = 1
  private pending = new Map<number, Pending>()
  private listeners = new Set<(s: JudgeStatus) => void>()
  status: JudgeStatus = 'idle'

  onStatus(fn: (s: JudgeStatus) => void) {
    this.listeners.add(fn)
    fn(this.status)
    return () => { this.listeners.delete(fn) }
  }

  private setStatus(s: JudgeStatus) {
    this.status = s
    this.listeners.forEach((fn) => fn(s))
  }

  private spawn() {
    const worker = new Worker(new URL('./pyodide.worker.ts', import.meta.url), { type: 'module' })
    worker.onmessage = (e: MessageEvent<WorkerResponse>) => {
      const p = this.pending.get(e.data.id)
      if (!p) return
      this.pending.delete(e.data.id)
      if (p.timer) clearTimeout(p.timer)
      if (e.data.ok) p.resolve(e.data.result)
      else p.reject(new Error(e.data.error))
    }
    worker.onerror = (e) => {
      this.pending.forEach((p) => p.reject(new Error(e.message || 'Worker crashed')))
      this.pending.clear()
      this.reset()
    }
    this.worker = worker
    this.setStatus('loading')
    this.ready = this.send({ kind: 'warmup' }, BOOT_TIMEOUT_MS).then(
      () => this.setStatus('ready'),
      (err) => { this.reset(); throw err },
    )
  }

  private reset() {
    this.worker?.terminate()
    this.worker = null
    this.ready = null
    this.setStatus('idle')
  }

  private send(body: DistributiveOmit<WorkerRequest, 'id'>, timeoutMs: number): Promise<unknown> {
    const id = this.nextId++
    return new Promise((resolve, reject) => {
      const pending: Pending = { resolve, reject }
      pending.timer = window.setTimeout(() => {
        this.pending.delete(id)
        reject(new TimeoutError())
      }, timeoutMs)
      this.pending.set(id, pending)
      this.worker!.postMessage({ ...body, id } as WorkerRequest)
    })
  }

  async warmup() {
    if (!this.worker) this.spawn()
    await this.ready
  }

  async exampleInputs(testCode: string): Promise<string[]> {
    await this.warmup()
    return (await this.send({ kind: 'cases', testCode, limit: RUN_CASES }, 10_000)) as string[]
  }

  async judge(args: { preamble: string; code: string; entryPoint: string; testCode: string; mode: 'run' | 'submit'; timeLimitMs?: number }): Promise<JudgeResult> {
    const limitMs = args.timeLimitMs ?? TIME_LIMIT_MS
    await this.warmup()
    this.setStatus('running')
    try {
      const result = (await this.send(
        {
          kind: 'judge', preamble: args.preamble, code: args.code, entryPoint: args.entryPoint,
          testCode: args.testCode, limit: args.mode === 'run' ? RUN_CASES : null,
        },
        limitMs,
      )) as JudgeResult
      this.setStatus('ready')
      return result
    } catch (err) {
      if (err instanceof TimeoutError) {
        // the only reliable way to stop a runaway loop: kill the worker
        this.reset()
        return { verdict: 'Time Limit Exceeded', passed: 0, total: 0, cases: [], error: `Your code ran longer than ${limitMs / 1000}s.` }
      }
      this.setStatus(this.worker ? 'ready' : 'idle')
      throw err
    }
  }
}

class TimeoutError extends Error {}

export type JudgeStatus = 'idle' | 'loading' | 'ready' | 'running'
export const judge = new Judge()
