import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { CompanyCount, Interview } from '../api/types'
import ProblemLink from '../components/ProblemLink'
import { fmtClock, useCountdown } from '../lib/time'

export function InterviewStart() {
  const [companies, setCompanies] = useState<CompanyCount[]>([])
  const [company, setCompany] = useState('')
  const [history, setHistory] = useState<Interview[]>([])
  const [error, setError] = useState('')
  const navigate = useNavigate()
  useEffect(() => {
    api.companies().then((c) => { setCompanies(c); setCompany(c[0]?.slug ?? '') }).catch(() => {})
    api.interviews().then(setHistory).catch(() => {})
  }, [])
  const start = async () => {
    try { navigate(`/interview/${(await api.startInterview(company)).id}`) } catch (e) { setError((e as Error).message) }
  }
  return (
    <div className="container">
      <h1>Mock interview</h1>
      <div className="card">
        <p>45 minutes, 2 real problems the company has asked. Talk out loud while you solve, like in a real interview.</p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <select className="input" value={company} onChange={(e) => setCompany(e.target.value)} style={{ maxWidth: 320 }}>
            {companies.map((c) => <option key={c.slug} value={c.slug}>{c.name} ({c.count})</option>)}
          </select>
          <button className="btn btn-primary" onClick={start} disabled={!company}>Start 45:00</button>
        </div>
        {error && <p className="error-text">{error}</p>}
      </div>
      {history.length > 0 && (
        <div className="card">
          <div className="section-title" style={{ marginTop: 0 }}>Past interviews</div>
          <table className="subs"><tbody>
            {history.map((h) => (
              <tr key={h.id}>
                <td><Link to={`/interview/${h.id}`}>{h.company.name}</Link></td>
                <td>{h.problems.filter((p) => p.solved).length}/2 solved</td>
                <td>{h.score === null ? (h.seconds_left > 0 ? 'in progress' : 'not finished') : `${h.score} pts`}</td>
                <td className="muted">{new Date(h.started_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody></table>
        </div>
      )}
    </div>
  )
}

export function InterviewSession() {
  const { id = '0' } = useParams()
  const [s, setS] = useState<Interview | null>(null)
  const left = useCountdown(s && !s.finished_at ? s.ends_at : null)
  useEffect(() => {
    const load = () => api.interview(Number(id)).then(setS).catch(() => {})
    load()
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [id])
  if (!s) return <div className="empty"><span className="spinner" /></div>
  const done = s.finished_at !== null || left === 0
  return (
    <div className="container">
      <h1>{s.company.name} interview</h1>
      <div className={`card timer ${left < 300 && !done ? 'urgent' : ''}`}>
        {s.finished_at ? <b>Finished · score {s.score} / 100</b> : <b>{done ? 'Time is up' : fmtClock(left)}</b>}
        {!s.finished_at && <button className="btn" onClick={() => api.finishInterview(s.id).then(setS)}>Finish &amp; score</button>}
      </div>
      <div className="card">
        {s.problems.map((p) => <ProblemLink key={p.slug} p={p} query={`?interview=${s.id}`} />)}
      </div>
      <p className="faint">Scoring: 40 points per solved problem, plus up to 20 for finishing both early. Only Accepted submissions made during the 45 minutes count.</p>
    </div>
  )
}

export function InterviewBanner({ id }: { id: number }) {
  const [s, setS] = useState<Interview | null>(null)
  useEffect(() => { api.interview(id).then(setS).catch(() => {}) }, [id])
  const left = useCountdown(s && !s.finished_at ? s.ends_at : null)
  if (!s) return null
  return (
    <div className={`interview-banner ${left < 300 ? 'urgent' : ''}`}>
      <Link to={`/interview/${s.id}`}>{s.company.name} mock interview</Link>
      <b>{s.finished_at ? 'finished' : fmtClock(left)}</b>
    </div>
  )
}
