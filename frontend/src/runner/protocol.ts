/// <reference types="vite/client" />
import type { Verdict } from '../api/types'

export interface CaseResult {
  index: number
  input: string
  passed?: boolean
  output?: string
  expected?: string
  error?: string
}

export interface JudgeResult {
  verdict: Verdict
  passed: number
  total: number
  cases: CaseResult[]
  runtime_ms?: number
  stdout?: string
  error?: string
}

export interface JudgeRequest {
  id: number
  kind: 'judge'
  preamble: string
  code: string
  entryPoint: string
  testCode: string
  limit: number | null
}

export interface CasesRequest { id: number; kind: 'cases'; testCode: string; limit: number }
export interface WarmupRequest { id: number; kind: 'warmup' }

export type WorkerRequest = JudgeRequest | CasesRequest | WarmupRequest

export type WorkerResponse =
  | { id: number; ok: true; result: unknown }
  | { id: number; ok: false; error: string }

export const PYODIDE_VERSION = '0.27.2'
// Defaults to the jsDelivr CDN. Set VITE_PYODIDE_URL=/pyodide/ after `npm run pyodide:local`
// to self-host the runtime (offline / air-gapped setups).
export const PYODIDE_INDEX_URL: string =
  import.meta.env?.VITE_PYODIDE_URL ?? `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`

// Thin JSON wrappers so results cross the JS/Python boundary as plain strings.
export const JSON_HELPERS = `
import json as _json
def run_json(*args):
    return _json.dumps(run(*args))
def cases_json(test_code):
    return _json.dumps(parse_cases(test_code))
`
