import { Link } from 'react-router-dom'
import type { BriefProblem } from '../api/types'
import { StatusIcon } from './common'

export default function ProblemLink({ p, query = '' }: { p: BriefProblem; query?: string }) {
  const status = p.status ?? (p.solved ? 'solved' : 'todo')
  return (
    <Link to={`/problems/${p.slug}${query}`} className="plan-row">
      <StatusIcon status={status} />
      <span className="plan-title">{p.frontend_id ? `${p.frontend_id}. ` : ''}{p.title}</span>
      <span className={`diff-${p.difficulty}`}>{p.difficulty}</span>
    </Link>
  )
}
