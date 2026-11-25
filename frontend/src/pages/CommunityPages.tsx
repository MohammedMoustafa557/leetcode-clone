import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { ContestInfo, Difficulty, LeaderRow, PublicProfile } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import ProblemLink from '../components/ProblemLink'
import { fmtClock, useCountdown } from '../lib/time'

function MiniRing({ label, solved, total, color }: { label: Difficulty; solved: number; total: number; color: string }) {
  const r = 30, c = 2 * Math.PI * r, pct = total ? solved / total : 0
  return (
    <div className="mini-ring">
      <svg width="76" height="76" viewBox="0 0 76 76" role="img" aria-label={`${label}: ${solved} of ${total}`}>
        <circle cx="38" cy="38" r={r} stroke="var(--bg-3)" strokeWidth="6" fill="none" />
        <circle cx="38" cy="38" r={r} stroke={color} strokeWidth="6" fill="none" strokeDasharray={`${c * pct} ${c}`} strokeLinecap="round" transform="rotate(-90 38 38)" />
        <text x="38" y="43" textAnchor="middle" fill="var(--text)" fontSize="16" fontWeight="700">{solved}</text>
      </svg>
      <div className={`diff-${label}`}>{label}</div>
      <div className="faint" style={{ fontSize: 11 }}>of {total}</div>
    </div>
  )
}

export function UserPage() {
  const { username = '' } = useParams()
  const [p, setP] = useState<PublicProfile | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api.profile(username).then(setP).catch((e: Error) => setError(e.message)) }, [username])
  if (error) return <div className="empty">{error}</div>
  if (!p) return <div className="empty"><span className="spinner" /></div>
  return (
    <div className="container">
      <div className="profile-grid">
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span className="avatar" style={{ width: 52, height: 52, fontSize: 22 }}>{p.username[0]}</span>
            <div><div style={{ fontWeight: 700, fontSize: 18 }}>{p.username}</div>
              <div className="faint" style={{ fontSize: 12 }}>Joined {new Date(p.joined).toLocaleDateString()}</div></div>
          </div>
          <div className="stat-tiles" style={{ marginTop: 16 }}>
            <div className="stat-tile"><div className="num">{p.rating}</div><div className="lbl">Contest rating</div></div>
            <div className="stat-tile"><div className="num">{p.global_rank ?? '–'}</div><div className="lbl">Global rank</div></div>
            <div className="stat-tile"><div className="num">{p.points}</div><div className="lbl">Points</div></div>
            <div className="stat-tile"><div className="num">{p.streak}</div><div className="lbl">Streak (max {p.max_streak})</div></div>
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20, minWidth: 0 }}>
          <div className="card rings">
            <MiniRing label="Easy" solved={p.solved.Easy} total={p.totals.Easy} color="var(--easy)" />
            <MiniRing label="Medium" solved={p.solved.Medium} total={p.totals.Medium} color="var(--medium)" />
            <MiniRing label="Hard" solved={p.solved.Hard} total={p.totals.Hard} color="var(--hard)" />
          </div>
          <div className="card">
            <div className="section-title" style={{ marginTop: 0 }}>Badges</div>
            <div className="badges">
              {p.badges.map((b) => (
                <div key={b.id} className={`badge ${b.earned ? 'earned' : ''}`} title={b.description}>
                  <div className="badge-name">{b.name}</div><div className="faint" style={{ fontSize: 11 }}>{b.description}</div>
                </div>
              ))}
            </div>
          </div>
          {p.contest_history.length > 0 && (
            <div className="card">
              <div className="section-title" style={{ marginTop: 0 }}>Contest history</div>
              <table className="subs"><tbody>
                {p.contest_history.map((c) => (
                  <tr key={c.number}><td><Link to={`/contest/${c.number}`}>{c.title}</Link></td><td>rank {c.rank}</td>
                    <td className={c.rating_after >= c.rating_before ? 'v-Accepted' : 'v-Wrong'}>{c.rating_before} → {c.rating_after}</td></tr>
                ))}
              </tbody></table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function LeaderboardPage() {
  const [sort, setSort] = useState<'points' | 'streak' | 'rating'>('points')
  const [rows, setRows] = useState<LeaderRow[]>([])
  useEffect(() => { api.leaderboard(sort).then(setRows).catch(() => {}) }, [sort])
  return (
    <div className="container">
      <h1>Leaderboard</h1>
      <div className="tabs">
        {(['points', 'streak', 'rating'] as const).map((s) => (
          <button key={s} className={`tab ${sort === s ? 'active' : ''}`} onClick={() => setSort(s)}>{s[0].toUpperCase() + s.slice(1)}</button>
        ))}
      </div>
      <table className="table">
        <thead><tr><th>#</th><th>User</th><th>Points</th><th>Solved</th><th>Streak</th><th>Rating</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.username}><td>{r.rank}</td><td><Link to={`/u/${r.username}`}>{r.username}</Link></td>
              <td>{r.points}</td><td>{r.solved}</td><td>{r.streak}</td><td>{r.rating}</td></tr>
          ))}
        </tbody>
      </table>
      <p className="faint">Points: Easy 10, Medium 20, Hard 40 per solved problem. Rating changes after each weekly contest (Elo).</p>
    </div>
  )
}

export function ContestPage() {
  const { number } = useParams()
  const { user } = useAuth()
  const [c, setC] = useState<ContestInfo | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    const load = () => (number ? api.contest(Number(number)) : api.currentContest()).then(setC).catch((e: Error) => setError(e.message))
    load()
    const t = setInterval(load, 20000)
    return () => clearInterval(t)
  }, [number])
  const target = c ? (c.phase === 'upcoming' ? c.starts_at : c.phase === 'running' ? c.ends_at : null) : null
  const left = useCountdown(target)
  if (error) return <div className="empty">{error}</div>
  if (!c) return <div className="empty"><span className="spinner" /></div>
  return (
    <div className="container">
      <h1>{c.title}</h1>
      <div className="card timer">
        <div>
          <div>{new Date(c.starts_at).toLocaleString()} – {new Date(c.ends_at).toLocaleTimeString()}</div>
          <b>{c.phase === 'upcoming' ? `Starts in ${fmtClock(left)}` : c.phase === 'running' ? `Ends in ${fmtClock(left)}` : c.rated ? 'Finished · ratings updated' : 'Finished'}</b>
        </div>
        {c.phase !== 'finished' && (user
          ? (c.registered ? <span className="v-Accepted">Registered</span>
            : <button className="btn btn-primary" onClick={() => api.registerContest(c.number).then(setC)}>Register</button>)
          : <Link className="btn" to="/login">Sign in to register</Link>)}
      </div>
      {c.problems.length > 0 && (
        <div className="card">
          {c.problems.map((p) => <div key={p.slug} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span className="faint">Q{p.index} · {p.points} pts</span><div style={{ flex: 1 }}><ProblemLink p={p} /></div></div>)}
        </div>
      )}
      {c.standings.length > 0 && (
        <table className="table">
          <thead><tr><th>Rank</th><th>User</th><th>Score</th><th>Finish time</th><th>Rating</th></tr></thead>
          <tbody>
            {c.standings.map((s) => (
              <tr key={s.username}><td>{s.rank}</td><td><Link to={`/u/${s.username}`}>{s.username}</Link></td><td>{s.score}</td>
                <td>{fmtClock(s.penalty_seconds)}</td>
                <td>{s.rating_after !== null ? `${s.rating_before} → ${s.rating_after}` : '–'}</td></tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="faint">4 problems (Q1 Easy … Q4 Hard), 90 minutes. Ranking: score, then finish time (+5 min per wrong submission before Accepted). {c.participants} registered.</p>
    </div>
  )
}
