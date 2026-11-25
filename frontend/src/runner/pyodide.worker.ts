/// <reference lib="webworker" />
// Runs untrusted user code inside Pyodide (CPython compiled to WebAssembly),
// isolated in a Web Worker so an infinite loop can be killed by terminating the worker.
import harnessSource from '@runner/harness.py?raw'
import { JSON_HELPERS, PYODIDE_INDEX_URL, type WorkerRequest, type WorkerResponse } from './protocol'

interface PyProxy { destroy?: () => void }
interface Pyodide {
  runPython: (code: string) => unknown
  loadPackage: (names: string[]) => Promise<void>
  globals: { get: (name: string) => ((...args: unknown[]) => unknown) & PyProxy }
}

let pyodidePromise: Promise<Pyodide> | null = null
const loadedPackages = new Set<string>()

async function getPyodide(): Promise<Pyodide> {
  if (!pyodidePromise) {
    pyodidePromise = (async () => {
      const mod = await import(/* @vite-ignore */ `${PYODIDE_INDEX_URL}pyodide.mjs`)
      const py: Pyodide = await mod.loadPyodide({ indexURL: PYODIDE_INDEX_URL })
      py.runPython(harnessSource)
      py.runPython(JSON_HELPERS)
      return py
    })()
  }
  return pyodidePromise
}

async function ensurePackages(py: Pyodide, preamble: string) {
  if (preamble.includes('sortedcontainers') && !loadedPackages.has('sortedcontainers')) {
    await py.loadPackage(['sortedcontainers'])
    loadedPackages.add('sortedcontainers')
  }
}

function callJson(py: Pyodide, fn: string, ...args: unknown[]): unknown {
  const f = py.globals.get(fn)
  try {
    return JSON.parse(f(...args) as string)
  } finally {
    f.destroy?.()
  }
}

self.onmessage = async (event: MessageEvent<WorkerRequest>) => {
  const msg = event.data
  const reply = (r: WorkerResponse) => self.postMessage(r)
  try {
    const py = await getPyodide()
    if (msg.kind === 'warmup') return reply({ id: msg.id, ok: true, result: null })
    if (msg.kind === 'cases') {
      const cases = callJson(py, 'cases_json', msg.testCode) as { actual: string | null; source: string }[]
      const labels = cases.slice(0, msg.limit).map((c) => {
        const expr = c.actual ?? c.source
        const m = expr.match(/candidate\((.*)\)$/s)
        return m ? m[1] : expr
      })
      return reply({ id: msg.id, ok: true, result: labels })
    }
    await ensurePackages(py, msg.preamble)
    const result = callJson(py, 'run_json', msg.preamble, msg.code, msg.entryPoint, msg.testCode, msg.limit)
    reply({ id: msg.id, ok: true, result })
  } catch (err) {
    reply({ id: msg.id, ok: false, error: err instanceof Error ? err.message : String(err) })
  }
}
