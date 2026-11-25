import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Daily, PlanDetail, PlanSummary } from '../api/types'
import ProblemLink from '../components/ProblemLink'

export function DailyCard() {
  const [daily, setDaily] = useState<Daily | null>(null)
  useEffect(() => { api.daily().then(setDaily).catch(() => {}) }, [])
  if (!daily) return null
  return (
    <div className="card daily-card">
      <div>
        <div className="faint" style={{ fontSize: 12 }}>Problem of the day · {daily.date}{daily.group ? ` · ${daily.group}` : ''}</div>
        <Link to={`/problems/${daily.problem.slug}`} style={{ fontWeight: 600 }}>{daily.problem.title}</Link>{' '}
        <span className={`diff-${daily.problem.difficulty}`}>{daily.problem.difficulty}</span>
      </div>
      {daily.problem.status === 'solved' ? <span className="v-Accepted">Solved today's problem</span>
        : <Link className="btn btn-primary" to={`/problems/${daily.problem.slug}`}>Solve</Link>}
    </div>
  )
}

export function PlansPage() {
  const [plans, setPlans] = useState<PlanSummary[]>([])
  useEffect(() => { api.plans().then(setPlans).catch(() => {}) }, [])
  return (
    <div className="container">
      <h1>Study plans</h1>
      <DailyCard />
      <div className="card-grid">
        {plans.map((p) => (
          <Link key={p.id} to={`/plans/${p.id}`} className="card plan-card">
            <h3>{p.title}</h3>
            <p className="muted">{p.description}</p>
            <div className="bar"><div style={{ width: `${(100 * p.solved) / Math.max(1, p.matched)}%`, background: 'var(--accent)' }} /></div>
            <div className="faint" style={{ fontSize: 12, marginTop: 6 }}>
              {p.solved}/{p.matched} solved · {p.groups} topics · {p.matched} of {p.upstream_total} listed problems are in this catalog
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

export function PlanPage() {
  const { id = '' } = useParams()
  const [plan, setPlan] = useState<PlanDetail | null>(null)
  useEffect(() => { api.plan(id).then(setPlan).catch(() => {}) }, [id])
  if (!plan) return <div className="empty"><span className="spinner" /></div>
  return (
    <div className="container">
      <Link to="/plans" className="faint">← Study plans</Link>
      <h1>{plan.title}</h1>
      <p className="muted">{plan.description} Showing {plan.matched} of {plan.upstream_total} (only problems available in this catalog).</p>
      {plan.groups.map((g) => {
        const solved = g.problems.filter((p) => p.status === 'solved').length
        return (
          <details key={g.name} className="card plan-group" open>
            <summary><b>{g.name}</b> <span className="faint">{solved}/{g.problems.length}</span></summary>
            {g.problems.map((p) => <ProblemLink key={p.slug} p={p} />)}
          </details>
        )
      })}
    </div>
  )
}
