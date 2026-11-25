import { useState } from 'react'
import type { JudgeResult } from '../runner/protocol'

interface Props {
  inputs: string[]
  result: JudgeResult | null
  mode: 'run' | 'submit' | null
  busy: boolean
  tab: 'testcase' | 'result'
  onTab: (t: 'testcase' | 'result') => void
}

export default function Console({ inputs, result, mode, busy, tab, onTab }: Props) {
  const [caseIdx, setCaseIdx] = useState(0)
  return (
    <>
      <div className="tabs">
        <button className={`tab ${tab === 'testcase' ? 'active' : ''}`} onClick={() => onTab('testcase')}>Testcase</button>
        <button className={`tab ${tab === 'result' ? 'active' : ''}`} onClick={() => onTab('result')}>Test Result</button>
      </div>
      <div className="panel-body">
        {tab === 'testcase' ? (
          inputs.length ? (
            <>
              <div className="case-tabs">
                {inputs.map((_, i) => (
                  <button key={i} className={`case-tab ${i === caseIdx ? 'active' : ''}`} onClick={() => setCaseIdx(i)}>Case {i + 1}</button>
                ))}
              </div>
              <div className="io-box">{inputs[Math.min(caseIdx, inputs.length - 1)]}</div>
            </>
          ) : <p className="muted">Loading the Python runtime…</p>
        ) : (
          <ResultView result={result} mode={mode} busy={busy} />
        )}
      </div>
    </>
  )
}

function ResultView({ result, mode, busy }: { result: JudgeResult | null; mode: 'run' | 'submit' | null; busy: boolean }) {
  const [caseIdx, setCaseIdx] = useState(0)
  if (busy) return <p className="muted"><span className="spinner" /> &nbsp;{mode === 'submit' ? 'Judging all test cases…' : 'Running…'}</p>
  if (!result) return <p className="muted">You must run your code first.</p>

  const cls = `v-${result.verdict.split(' ')[0]}`
  const failed = result.cases.find((c) => c.passed === false || c.error)

  if (mode === 'submit') {
    return (
      <div>
        <div className={`verdict ${cls}`}>
          {result.verdict}
          <small>{result.passed} / {result.total} testcases passed{result.runtime_ms != null ? ` · ${Math.round(result.runtime_ms)} ms` : ''}</small>
        </div>
        {result.error && <div className="error-box" style={{ marginTop: 10 }}>{result.error}</div>}
        {failed && !failed.error && (
          <>
            <div className="io-label">Input</div><div className="io-box">{failed.input}</div>
            {failed.output !== undefined && <><div className="io-label">Output</div><div className="io-box">{failed.output}</div></>}
            {failed.expected !== undefined && <><div className="io-label">Expected</div><div className="io-box">{failed.expected}</div></>}
          </>
        )}
        {result.stdout && <><div className="io-label">Stdout</div><div className="io-box">{result.stdout}</div></>}
      </div>
    )
  }

  const shown = result.cases
  const current = shown[Math.min(caseIdx, Math.max(0, shown.length - 1))]
  return (
    <div>
      <div className={`verdict ${cls}`}>
        {result.verdict}
        {result.runtime_ms != null && <small>Runtime: {Math.round(result.runtime_ms)} ms</small>}
      </div>
      {result.error && <div className="error-box" style={{ margin: '10px 0' }}>{result.error}</div>}
      {shown.length > 0 && (
        <>
          <div className="case-tabs" style={{ marginTop: 10 }}>
            {shown.map((c, i) => (
              <button key={i} className={`case-tab ${i === caseIdx ? 'active' : ''}`} onClick={() => setCaseIdx(i)}>
                <span className="dot" style={{ background: c.passed ? 'var(--green)' : 'var(--red)' }} /> Case {i + 1}
              </button>
            ))}
          </div>
          {current && (
            <>
              <div className="io-label">Input</div><div className="io-box">{current.input}</div>
              {current.output !== undefined && <><div className="io-label">Output</div><div className="io-box">{current.output}</div></>}
              {current.expected !== undefined && <><div className="io-label">Expected</div><div className="io-box">{current.expected}</div></>}
            </>
          )}
        </>
      )}
      {result.stdout && <><div className="io-label">Stdout</div><div className="io-box">{result.stdout}</div></>}
    </div>
  )
}
