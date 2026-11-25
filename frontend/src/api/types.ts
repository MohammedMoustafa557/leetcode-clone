export type Difficulty = 'Easy' | 'Medium' | 'Hard'
export type Verdict = 'Accepted' | 'Wrong Answer' | 'Runtime Error' | 'Compile Error' | 'Time Limit Exceeded'
export type ProblemStatus = 'solved' | 'attempted' | 'todo'

export interface User { id: number; username: string; email: string; created_at: string }
export interface TokenResponse { access_token: string; token_type: string; user: User }

export interface TagCount { name: string; slug: string; count: number }
export type CompanyCount = TagCount

export interface ProblemSummary {
  id: number
  frontend_id: number
  slug: string
  title: string
  difficulty: Difficulty
  tags: string[]
  company_count: number
  frequency: number | null
  status: ProblemStatus
}

export interface ProblemPage { items: ProblemSummary[]; total: number; page: number; page_size: number }

export interface ProblemCompany { name: string; slug: string; frequency: number; recency: string }

export interface ProblemDetail {
  id: number
  frontend_id: number
  slug: string
  title: string
  difficulty: Difficulty
  description: string
  starter_code: string
  entry_point: string
  preamble: string
  test_code: string
  test_count: number
  released: string | null
  heavy_tests: boolean
  tags: TagCount[]
  companies: ProblemCompany[]
  status: ProblemStatus
}

export interface Submission {
  id: number
  problem_slug: string
  problem_title: string
  verdict: Verdict
  passed: number
  total: number
  runtime_ms: number | null
  language: string
  created_at: string
  code: string | null
}

export interface Stats {
  solved: number
  attempted: number
  total_problems: number
  submissions: number
  acceptance_rate: number
  by_difficulty: Record<Difficulty, { solved: number; total: number }>
  streak: number
  max_streak: number
  calendar: Record<string, number>
  top_tags: TagCount[]
}

export interface TagStat { name: string; slug: string; attempted: number; solved: number; submissions: number; accuracy: number }
export interface StatsExtra { tag_stats: TagStat[]; strengths: TagStat[]; weaknesses: TagStat[] }

export interface BriefProblem { slug: string; title: string; difficulty: Difficulty; frontend_id?: number; status?: ProblemStatus; solved?: boolean }
export interface PlanSummary { id: string; title: string; description: string; matched: number; upstream_total: number; groups: number; solved: number }
export interface PlanDetail { id: string; title: string; description: string; matched: number; upstream_total: number; groups: { name: string; problems: BriefProblem[] }[] }
export interface Daily { date: string; group: string | null; problem: BriefProblem }

export interface Guide {
  source: 'auto' | 'llm'
  hints: string[]
  explanation: string
  time_complexity: string
  space_complexity: string
  complexity_note: string
  techniques: string[]
  interview_sentences: { en: string; ar: string }[]
}

export interface Interview {
  id: number
  company: { name: string; slug: string }
  started_at: string
  ends_at: string
  finished_at: string | null
  seconds_left: number
  score: number | null
  problems: BriefProblem[]
}

export interface Badge { id: string; name: string; description: string; earned: boolean }
export interface PublicProfile {
  username: string
  joined: string
  solved: Record<Difficulty, number>
  totals: Record<Difficulty, number>
  points: number
  streak: number
  max_streak: number
  rating: number
  global_rank: number | null
  contests: number
  badges: Badge[]
  contest_history: { number: number; title: string; rank: number; rating_before: number; rating_after: number; score: number }[]
}
export interface LeaderRow { rank: number; username: string; points: number; solved: number; streak: number; max_streak: number; rating: number }
export interface ContestInfo {
  number: number
  title: string
  starts_at: string
  ends_at: string
  phase: 'upcoming' | 'running' | 'finished'
  rated: boolean
  registered: boolean
  participants: number
  problems: (BriefProblem & { index: number; points: number })[]
  standings: { rank: number; username: string; score: number; penalty_seconds: number; rating_before: number | null; rating_after: number | null }[]
}
