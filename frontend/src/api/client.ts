import { local } from '../lib/storage'
import type {
  ContestInfo, Daily, Guide, Interview, LeaderRow, PlanDetail, PlanSummary, PublicProfile, StatsExtra,
  CompanyCount, ProblemDetail, ProblemPage, ProblemSummary, Stats, Submission, TagCount, TokenResponse, User, Verdict,
} from './types'

const BASE = import.meta.env.VITE_API_URL ?? '/api'
const TOKEN_KEY = 'codearena.token'

export const tokenStore = {
  get: () => local.get(TOKEN_KEY),
  set: (t: string) => local.set(TOKEN_KEY, t),
  clear: () => local.remove(TOKEN_KEY),
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = tokenStore.get()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const res = await fetch(`${BASE}${path}`, { ...init, headers })
  if (!res.ok) {
    let message = res.statusText
    try {
      const body = await res.json()
      message = typeof body.detail === 'string' ? body.detail : body.detail?.[0]?.msg ?? message
    } catch { /* not json */ }
    if (res.status === 401 && token) tokenStore.clear()
    throw new ApiError(res.status, message)
  }
  return res.json() as Promise<T>
}

function qs(params: Record<string, string | number | string[] | undefined | null>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue
    if (Array.isArray(v)) v.forEach((x) => sp.append(k, x))
    else sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

export interface ProblemQuery {
  q?: string
  difficulty?: string
  tag?: string[]
  company?: string
  status?: string
  sort?: string
  order?: string
  page?: number
  page_size?: number
}

export const api = {
  register: (username: string, email: string, password: string) =>
    request<TokenResponse>('/auth/register', { method: 'POST', body: JSON.stringify({ username, email, password }) }),
  login: (login: string, password: string) =>
    request<TokenResponse>('/auth/login', { method: 'POST', body: JSON.stringify({ login, password }) }),
  me: () => request<User>('/auth/me'),

  problems: (query: ProblemQuery) => request<ProblemPage>(`/problems${qs({ ...query })}`),
  problem: (slug: string) => request<ProblemDetail>(`/problems/${slug}`),
  solution: (slug: string) => request<{ slug: string; solution: string }>(`/problems/${slug}/solution`),
  random: (difficulty?: string) => request<ProblemSummary>(`/problems/random${qs({ difficulty })}`),
  tags: () => request<TagCount[]>('/tags'),
  companies: () => request<CompanyCount[]>('/companies'),

  submit: (body: {
    problem_slug: string; code: string; verdict: Verdict; passed: number; total: number; runtime_ms?: number | null
  }) => request<Submission>('/submissions', { method: 'POST', body: JSON.stringify(body) }),
  submissions: (problem_slug?: string, limit = 50) => request<Submission[]>(`/submissions${qs({ problem_slug, limit })}`),
  submission: (id: number) => request<Submission>(`/submissions/${id}`),
  stats: () => request<Stats & StatsExtra>('/me/stats'),

  plans: () => request<PlanSummary[]>('/plans'),
  plan: (id: string) => request<PlanDetail>(`/plans/${id}`),
  daily: () => request<Daily>('/daily'),
  guide: (slug: string) => request<Guide>(`/problems/${slug}/guide`),
  learn: <T>(section: 'patterns' | 'sql' | 'templates' | 'behavioral' | 'system-design') => request<T>(`/learn/${section}`),

  startInterview: (company_slug: string) =>
    request<Interview>('/interviews', { method: 'POST', body: JSON.stringify({ company_slug }) }),
  interview: (id: number) => request<Interview>(`/interviews/${id}`),
  interviews: () => request<Interview[]>('/interviews'),
  finishInterview: (id: number) => request<Interview>(`/interviews/${id}/finish`, { method: 'POST' }),

  docs: () => request<{ id: string; title: string; author: string; repo: string; license: string; license_url: string; notice?: string | null; chapters: number }[]>('/docs'),
  book: (id: string) => request<import('../pages/DocsPages').BookInfo>(`/docs/${id}`),
  chapter: (id: string, chapter: string) => request<{
    id: string; title: string; markdown: string; prev: { id: string; title: string } | null; next: { id: string; title: string } | null
    credit: import('../pages/DocsPages').Credit
  }>(`/docs/${id}/${chapter}`),
  profile: (username: string) => request<PublicProfile>(`/users/${encodeURIComponent(username)}`),
  leaderboard: (sort: 'points' | 'streak' | 'rating') => request<LeaderRow[]>(`/leaderboard${qs({ sort })}`),
  currentContest: () => request<ContestInfo>('/contests/current'),
  contest: (n: number) => request<ContestInfo>(`/contests/${n}`),
  registerContest: (n: number) => request<ContestInfo>(`/contests/${n}/register`, { method: 'POST' }),
}
