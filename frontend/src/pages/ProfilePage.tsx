import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Stats, StatsExtra, Submission, TagStat } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { timeAgo } from '../components/format'

function Heatmap({ calendar }: { calendar: Record<string, number> }) {
  const days: { date: string; count: number }[] = []
  const today = new Date()
  const start = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate() - 7 * 26 + 1))
  start.setUTCDate(start.getUTCDate() - start.getUTCDay()) // align to Sunday
  for (let d = new Date(start); d <= today; d.setUTCDate(d.getUTCDate() + 1)) {
    const iso = d.toISOString().slice(0, 10)
    days.push({ date: iso, count: calendar[iso] ?? 0 })
  }
  const level = (n: number) => (n === 0 ? '' : n < 2 ? 'l1' : n < 4 ? 'l2' : n < 7 ? 'l3' : 'l4')
  return (
    <div className="heatmap">
      {days.map((d) => <div key={d.date} className={level(d.count)} title={`${d.count} submission${d.count === 1 ? '' : 's'} on ${d.date}`} />)}
    </div>
  )
}

function Ring({ solved, total }: { solved: number; total: number }) {
  const r = 52
  const c = 2 * Math.PI * r
  const pct = total ? solved / total : 0
  return (
    <svg width="130" height="130" viewBox="0 0 130 130" role="img" aria-label={`${solved} of ${total} solved`}>
      <circle cx="65" cy="65" r={r} stroke="var(--bg-3)" strokeWidth="8" fill="none" />
      <circle cx="65" cy="65" r={r} stroke="var(--accent)" strokeWidth="8" fill="none" strokeDasharray={`${c * pct} ${c}`} strokeLinecap="round" transform="rotate(-90 65 65)" />
      <text x="65" y="62" textAnchor="middle" fill="var(--text)" fontSize="24" fontWeight="700">{solved}</text>
      <text x="65" y="82" textAnchor="middle" fill="var(--text-2)" fontSize="12">/ {total}</text>
    </svg>
  )
}

function TopicList({ title, rows }: { title: string; rows: TagStat[] }) {
  return (
    <div>
      <div style={{ fontWeight: 600, marginBottom: 6 }}>{title}</div>
      {rows.length === 0 ? <div className="faint">Not enough data yet.</div> : rows.map((t) => (
        <Link key={t.slug} to={`/problems?tag=${t.slug}`} className="topic-row">
          <span>{t.name}</span><span className="faint">{t.solved} solved · {t.accuracy}%</span>
        </Link>
      ))}
    </div>
  )
}

export default function ProfilePage() {
  const { user } = useAuth()
  const [stats, setStats] = useState<(Stats & StatsExtra) | null>(null)
  const [recent, setRecent] = useState<Submission[]>([])

  useEffect(() => {
    api.stats().then(setStats).catch(() => {})
    api.submissions(undefined, 20).then(setRecent).catch(() => {})
  }, [])

  if (!user || !stats) return <div className="empty"><span className="spinner" /></div>

  return (
    <div className="container">
      <div className="profile-grid">
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <span className="avatar" style={{ width: 52, height: 52, fontSize: 22 }}>{user.username[0]}</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: 18 }}>{user.username}</div>
              <div className="faint" style={{ fontSize: 12 }}>Joined {new Date(user.created_at).toLocaleDateString()}</div>
            </div>
          </div>
          <div className="progress-ring">
            <Ring solved={stats.solved} total={stats.total_problems} />
            <div className="diff-rows">
              {(['Easy', 'Medium', 'Hard'] as const).map((d) => (
                <div key={d}>
                  <div className="diff-row"><span className={`diff-${d}`}>{d}</span><span>{stats.by_difficulty[d].solved}/{stats.by_difficulty[d].total}</span></div>
                  <div className="bar"><div style={{ width: `${(100 * stats.by_difficulty[d].solved) / Math.max(1, stats.by_difficulty[d].total)}%`, background: `var(--${d.toLowerCase()})` }} /></div>
                </div>
              ))}
            </div>
          </div>
          {stats.top_tags.length > 0 && (
            <>
              <div className="section-title">Strongest topics</div>
              <div className="chip-list">
                {stats.top_tags.map((t) => <Link key={t.slug} to={`/problems?tag=${t.slug}`} className="pill">{t.name} <span className="count">×{t.count}</span></Link>)}
              </div>
            </>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20, minWidth: 0 }}>
          <div className="stat-tiles">
            <div className="stat-tile"><div className="num">{stats.streak}</div><div className="lbl">Current streak (days)</div></div>
            <div className="stat-tile"><div className="num">{stats.max_streak}</div><div className="lbl">Longest streak</div></div>
            <div className="stat-tile"><div className="num">{stats.submissions}</div><div className="lbl">Submissions</div></div>
            <div className="stat-tile"><div className="num">{stats.acceptance_rate}%</div><div className="lbl">Acceptance rate</div></div>
            <div className="stat-tile"><div className="num">{stats.attempted}</div><div className="lbl">Attempted, not solved</div></div>
          </div>
          <div className="card">
            <div className="section-title" style={{ marginTop: 0 }}>Submissions in the last 26 weeks</div>
            <Heatmap calendar={stats.calendar} />
          </div>
          <div className="card">
            <div className="section-title" style={{ marginTop: 0 }}>Topics</div>
            {stats.tag_stats.length === 0 ? <p className="muted">Submit a few problems to see your strong and weak topics.</p> : (
              <div className="topic-split">
                <TopicList title="Strengths" rows={stats.strengths} />
                <TopicList title="Needs practice" rows={stats.weaknesses} />
              </div>
            )}
            <Link to={`/u/${user.username}`} className="faint">Public profile, rating and badges →</Link>
          </div>
          <div className="card">
            <div className="section-title" style={{ marginTop: 0 }}>Recent submissions</div>
            {recent.length === 0 ? <p className="muted">Nothing yet. <Link to="/problems" style={{ color: 'var(--blue)' }}>Solve your first problem</Link>.</p> : (
              <table className="subs">
                <tbody>
                  {recent.map((s) => (
                    <tr key={s.id}>
                      <td><Link to={`/problems/${s.problem_slug}`}>{s.problem_title}</Link></td>
                      <td className={`v-${s.verdict.split(' ')[0]}`}>{s.verdict}</td>
                      <td className="muted" style={{ textAlign: 'right' }}>{timeAgo(s.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
