import type { Difficulty, ProblemStatus } from '../api/types'

export function DifficultyText({ value }: { value: Difficulty }) {
  return <span className={`diff-${value}`}>{value === 'Medium' ? 'Med.' : value}</span>
}

export function StatusIcon({ status }: { status: ProblemStatus }) {
  if (status === 'solved') return <span className="status-icon status-solved" title="Solved">✓</span>
  if (status === 'attempted') return <span className="status-icon status-attempted" title="Attempted">◔</span>
  return <span className="status-icon" />
}
