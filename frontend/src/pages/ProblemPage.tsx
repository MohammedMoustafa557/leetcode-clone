import { Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type { ProblemDetail, Submission } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import Console from '../components/Console'
import Description from '../components/Description'
import { StatusIcon } from '../components/common'
import { RECENCY_LABEL, timeAgo } from '../components/format'
import { HEAVY_TIME_LIMIT_MS, judge, type JudgeStatus } from '../runner/judge'
import type { JudgeResult } from '../runner/protocol'
import { local } from '../lib/storage'
import GuidePanel from '../components/GuidePanel'
import { lazyRetry } from '../lib/lazyRetry'
import { InterviewBanner } from './InterviewPage'

const CodeEditor = lazyRetry(() => import('../components/CodeEditor'))

type LeftTab = 'description' | 'guide' | 'solution' | 'submissions'
const draftKey = (slug: string) => `codearena.draft.${slug}`

export default function ProblemPage() {
  const { slug = '' } = useParams()
  const { user } = useAuth()
  const [search] = useSearchParams()
  const interviewId = Number(search.get('interview')) || null
  const [problem, setProblem] = useState<ProblemDetail | null>(null)
  const [error, setError] = useState('')
  const [code, setCode] = useState('')
  const [leftTab, setLeftTab] = useState<LeftTab>('description')
  const [consoleTab, setConsoleTab] = useState<'testcase' | 'result'>('testcase')
  const [inputs, setInputs] = useState<string[]>([])
  const [result, setResult] = useState<JudgeResult | null>(null)
  const [mode, setMode] = useState<'run' | 'submit' | null>(null)
  const [busy, setBusy] = useState(false)
  const [runtime, setRuntime] = useState<JudgeStatus>(judge.status)
  const [solution, setSolution] = useState<string | null>(null)
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [viewing, setViewing] = useState<Submission | null>(null)
  const [toast, setToast] = useState('')
  const [fontSize, setFontSize] = useState(14)
  const [leftWidth, setLeftWidth] = useState(45)
  const dragging = useRef(false)

  useEffect(() => judge.onStatus(setRuntime), [])

  useEffect(() => {
    setProblem(null); setResult(null); setSolution(null); setLeftTab('description'); setConsoleTab('testcase'); setInputs([])
    api.problem(slug).then((p) => {
      setProblem(p)
      setCode(local.get(draftKey(slug)) ?? p.starter_code)
      judge.exampleInputs(p.test_code).then(setInputs).catch(() => {})
    }).catch((e: Error) => setError(e.message))
  }, [slug, user])

  const loadSubmissions = useCallback(() => {
    if (user) api.submissions(slug).then(setSubmissions).catch(() => {})
  }, [slug, user])
  useEffect(loadSubmissions, [loadSubmissions])

  useEffect(() => {
    if (!problem) return
    const t = setTimeout(() => local.set(draftKey(problem.slug), code), 400)
    return () => clearTimeout(t)
  }, [code, problem])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(''), 3500)
    return () => clearTimeout(t)
  }, [toast])

  const execute = useCallback(async (m: 'run' | 'submit') => {
    if (!problem || busy) return
    setBusy(true); setMode(m); setConsoleTab('result'); setResult(null)
    try {
      const res = await judge.judge({
        preamble: problem.preamble, code, entryPoint: problem.entry_point, testCode: problem.test_code, mode: m,
        timeLimitMs: problem.heavy_tests ? HEAVY_TIME_LIMIT_MS : undefined,
      })
      setResult(res)
      if (m === 'submit') {
        if (user) {
          await api.submit({
            problem_slug: problem.slug, code, verdict: res.verdict,
            passed: res.passed, total: res.verdict === 'Time Limit Exceeded' ? 0 : res.total, runtime_ms: res.runtime_ms ?? null,
          })
          loadSubmissions()
          if (res.verdict === 'Accepted') setProblem({ ...problem, status: 'solved' })
          else if (problem.status === 'todo') setProblem({ ...problem, status: 'attempted' })
        } else {
          setToast('Sign in to save your submissions and progress.')
        }
      }
    } catch (e) {
      setResult({ verdict: 'Runtime Error', passed: 0, total: 0, cases: [], error: (e as Error).message })
    } finally {
      setBusy(false)
    }
  }, [problem, code, busy, user, loadSubmissions])

  const showSolution = async () => {
    setLeftTab('solution')
    if (solution === null) setSolution((await api.solution(slug)).solution)
  }

  const onMouseMove = useCallback((e: MouseEvent) => {
    if (!dragging.current) return
    const pct = (e.clientX / window.innerWidth) * 100
    setLeftWidth(Math.min(70, Math.max(25, pct)))
  }, [])
  useEffect(() => {
    const up = () => { dragging.current = false; document.body.style.cursor = '' }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', up)
    return () => { window.removeEventListener('mousemove', onMouseMove); window.removeEventListener('mouseup', up) }
  }, [onMouseMove])

  if (error) return <div className="empty">{error} · <Link to="/problems" style={{ color: 'var(--blue)' }}>Back to problems</Link></div>
  if (!problem) return <div className="empty"><span className="spinner" /></div>

  return (
    <div className="workspace" style={{ ['--left-w' as string]: `${leftWidth}%` }}>
      <section className="panel panel-left">
        <div className="tabs">
          <button className={`tab ${leftTab === 'description' ? 'active' : ''}`} onClick={() => setLeftTab('description')}>Description</button>
          <button className={`tab ${leftTab === 'guide' ? 'active' : ''}`} onClick={() => setLeftTab('guide')}>Guide</button>
          {!interviewId && <button className={`tab ${leftTab === 'solution' ? 'active' : ''}`} onClick={showSolution}>Solution</button>}
          <button className={`tab ${leftTab === 'submissions' ? 'active' : ''}`} onClick={() => { setLeftTab('submissions'); setViewing(null) }}>Submissions</button>
        </div>
        {interviewId && <InterviewBanner id={interviewId} />}
        <div className="panel-body">
          {leftTab === 'guide' && <GuidePanel slug={problem.slug} />}
          {leftTab === 'description' && (
            <>
              <h1 className="problem-title">{problem.frontend_id}. {problem.title} <StatusIcon status={problem.status} /></h1>
              <div className="meta-row">
                <span className={`pill diff-${problem.difficulty}`}>{problem.difficulty}</span>
                {problem.tags.map((t) => <Link key={t.slug} className="pill" to={`/problems?tag=${t.slug}`}>{t.name}</Link>)}
              </div>
              <Description text={problem.description} />
              {problem.heavy_tests && (
                <p className="muted" style={{ fontSize: 13, borderLeft: '2px solid var(--medium)', paddingLeft: 10 }}>
                  This problem has a very heavy hidden test suite, so Submit gets a longer time limit
                  ({HEAVY_TIME_LIMIT_MS / 1000}s). Even an optimal solution can be slow in the browser.
                </p>
              )}
              {problem.companies.length > 0 && (
                <>
                  <div className="section-title">Companies <span className="faint" style={{ fontWeight: 400, fontSize: 12 }}>(community-collected)</span></div>
                  <div className="chip-list">
                    {problem.companies.slice(0, 40).map((c) => (
                      <Link key={c.slug} className="pill" to={`/problems?company=${c.slug}`} title={`Frequency ${c.frequency.toFixed(1)} · ${RECENCY_LABEL[c.recency] ?? c.recency}`}>
                        {c.name}
                      </Link>
                    ))}
                    {problem.companies.length > 40 && <span className="faint">+{problem.companies.length - 40} more</span>}
                  </div>
                </>
              )}
              <p className="faint" style={{ fontSize: 12, marginTop: 24 }}>
                {problem.test_count} test cases{problem.released ? ` · released around ${problem.released}` : ''} ·{' '}
                <a href={`https://leetcode.com/problems/${problem.slug}/`} target="_blank" rel="noreferrer" style={{ color: 'var(--blue)' }}>open on LeetCode</a>
              </p>
            </>
          )}
          {leftTab === 'solution' && (
            <>
              <p className="muted">Reference solution from LeetCodeDataset. Try for 30–45 minutes before reading it.</p>
              {solution === null ? <span className="spinner" /> : <pre className="io-box">{solution}</pre>}
            </>
          )}
          {leftTab === 'submissions' && (
            !user ? <p className="muted"><Link to="/login" style={{ color: 'var(--blue)' }}>Sign in</Link> to see your submissions.</p>
              : viewing ? (
                <>
                  <button className="btn btn-ghost" onClick={() => setViewing(null)}>← All submissions</button>
                  <div className={`verdict v-${viewing.verdict.split(' ')[0]}`} style={{ marginTop: 10 }}>{viewing.verdict} <small>{viewing.passed} / {viewing.total} · {timeAgo(viewing.created_at)}</small></div>
                  <pre className="io-box">{viewing.code}</pre>
                  <button className="btn" onClick={() => { setCode(viewing.code ?? ''); setToast('Loaded this submission into the editor.') }}>Load into editor</button>
                </>
              ) : submissions.length === 0 ? <p className="muted">No submissions yet.</p> : (
                <table className="subs">
                  <thead><tr><th>Status</th><th>Passed</th><th>Runtime</th><th>When</th></tr></thead>
                  <tbody>
                    {submissions.map((s) => (
                      <tr key={s.id} className="clickable" onClick={() => api.submission(s.id).then(setViewing)}>
                        <td className={`v-${s.verdict.split(' ')[0]}`}>{s.verdict}</td>
                        <td>{s.passed}/{s.total}</td>
                        <td>{s.runtime_ms != null ? `${Math.round(s.runtime_ms)} ms` : '—'}</td>
                        <td className="muted">{timeAgo(s.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
          )}
        </div>
      </section>

      <div className="splitter" onMouseDown={() => { dragging.current = true; document.body.style.cursor = 'col-resize' }} />

      <section className="panel-right">
        <div className="panel editor-panel">
          <div className="editor-toolbar">
            <span className="muted">Python3</span>
            <span className="spacer" />
            <select className="select" style={{ height: 28 }} value={fontSize} onChange={(e) => setFontSize(Number(e.target.value))} aria-label="Font size">
              {[12, 13, 14, 15, 16, 18].map((n) => <option key={n} value={n}>{n}px</option>)}
            </select>
            <button className="btn btn-ghost" onClick={() => { if (confirm('Reset to the starter code?')) setCode(problem.starter_code) }}>Reset</button>
          </div>
          <div className="editor-host">
            <Suspense fallback={<div className="empty"><span className="spinner" /></div>}>
              <CodeEditor value={code} onChange={setCode} onRun={() => execute('run')} onSubmit={() => execute('submit')} fontSize={fontSize} />
            </Suspense>
          </div>
        </div>
        <div className="panel console-panel">
          <Console inputs={inputs} result={result} mode={mode} busy={busy} tab={consoleTab} onTab={setConsoleTab} />
          <div className="console-actions">
            <span className="hint">
              {runtime === 'loading' && <><span className="spinner" /> Loading Python (first time only)…</>}
              {runtime === 'ready' && 'Python ready · Ctrl+\' run · Ctrl+Enter submit'}
            </span>
            <button className="btn" disabled={busy} onClick={() => execute('run')}>Run</button>
            <button className="btn btn-success" disabled={busy} onClick={() => execute('submit')}>Submit</button>
          </div>
        </div>
      </section>
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
