import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type { CompanyCount, ProblemPage, Stats, TagCount } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { DifficultyText, StatusIcon } from '../components/common'
import { DailyCard } from './PlansPage'

const PAGE_SIZE = 50

export default function ProblemsPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState<ProblemPage | null>(null)
  const [error, setError] = useState('')
  const [tags, setTags] = useState<TagCount[]>([])
  const [companies, setCompanies] = useState<CompanyCount[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [topicsOpen, setTopicsOpen] = useState(false)
  const [companyQuery, setCompanyQuery] = useState('')
  const [search, setSearch] = useState(params.get('q') ?? '')

  const query = useMemo(() => ({
    q: params.get('q') ?? undefined,
    difficulty: params.get('difficulty') ?? undefined,
    tag: params.getAll('tag'),
    company: params.get('company') ?? undefined,
    status: params.get('status') ?? undefined,
    sort: params.get('sort') ?? (params.get('company') ? 'frequency' : 'id'),
    order: params.get('order') ?? (params.get('company') ? 'desc' : 'asc'),
    page: Number(params.get('page') ?? 1),
    page_size: PAGE_SIZE,
  }), [params])

  useEffect(() => {
    api.tags().then(setTags).catch(() => {})
    api.companies().then(setCompanies).catch(() => {})
  }, [])

  useEffect(() => {
    if (user) api.stats().then(setStats).catch(() => {})
    else setStats(null)
  }, [user])

  useEffect(() => {
    let cancelled = false
    setError('')
    api.problems(query)
      .then((d) => { if (!cancelled) setData(d) })
      .catch((e: Error) => { if (!cancelled) setError(e.message) })
    return () => { cancelled = true }
  }, [query, user])

  // debounce the search box into the URL
  useEffect(() => {
    const t = setTimeout(() => {
      if ((params.get('q') ?? '') !== search) update({ q: search || null })
    }, 300)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search])

  function update(changes: Record<string, string | string[] | null>, resetPage = true) {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(changes)) {
      next.delete(k)
      if (Array.isArray(v)) v.forEach((x) => next.append(k, x))
      else if (v !== null && v !== '') next.set(k, v)
    }
    if (resetPage) next.delete('page')
    setParams(next)
  }

  const toggleTag = (slug: string) => {
    const current = params.getAll('tag')
    update({ tag: current.includes(slug) ? current.filter((t) => t !== slug) : [...current, slug] })
  }

  const setSort = (key: string) => {
    const order = query.sort === key && query.order === 'asc' ? 'desc' : 'asc'
    update({ sort: key, order }, false)
  }

  const pickOne = async () => {
    try {
      const p = await api.random(query.difficulty)
      navigate(`/problems/${p.slug}`)
    } catch (e) { setError((e as Error).message) }
  }

  const tagName = (slug: string) => tags.find((t) => t.slug === slug)?.name ?? slug
  const companyName = (slug: string) => companies.find((c) => c.slug === slug)?.name ?? slug
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1
  const sortMark = (key: string) => (query.sort === key ? (query.order === 'asc' ? ' ↑' : ' ↓') : '')
  const filteredCompanies = companies.filter((c) => c.name.toLowerCase().includes(companyQuery.toLowerCase()))
  const hasFilters = query.q || query.difficulty || query.tag.length || query.company || query.status

  return (
    <div className="container">
      <div className="list-layout">
        <section>
          <DailyCard />
          <div className={`topic-bar ${topicsOpen ? 'open' : ''}`}>
            {tags.map((t) => (
              <button key={t.slug} className={`pill ${query.tag.includes(t.slug) ? 'active' : ''}`} onClick={() => toggleTag(t.slug)}>
                {t.name} <span className="count">{t.count}</span>
              </button>
            ))}
          </div>
          {tags.length > 12 && (
            <button className="btn btn-ghost" style={{ marginTop: -8, marginBottom: 10 }} onClick={() => setTopicsOpen(!topicsOpen)}>
              {topicsOpen ? 'Show fewer topics' : `Show all ${tags.length} topics`}
            </button>
          )}

          <div className="filters">
            <input className="input" placeholder="Search by title or number" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search problems" />
            <select className="select" value={query.difficulty ?? ''} onChange={(e) => update({ difficulty: e.target.value || null })} aria-label="Difficulty">
              <option value="">Difficulty</option>
              <option>Easy</option><option>Medium</option><option>Hard</option>
            </select>
            <select className="select" value={query.status ?? ''} onChange={(e) => update({ status: e.target.value || null })} aria-label="Status" disabled={!user} title={user ? '' : 'Sign in to filter by status'}>
              <option value="">Status</option>
              <option value="todo">Todo</option><option value="attempted">Attempted</option><option value="solved">Solved</option>
            </select>
            <select className="select" value={query.company ?? ''} onChange={(e) => update({ company: e.target.value || null, sort: null, order: null })} aria-label="Company" style={{ maxWidth: 180 }}>
              <option value="">Company</option>
              {companies.map((c) => <option key={c.slug} value={c.slug}>{c.name} ({c.count})</option>)}
            </select>
            <button className="btn" onClick={pickOne} title="Open a random unsolved problem">Pick one</button>
          </div>

          {hasFilters ? (
            <div className="active-filters">
              {query.difficulty && <button className="pill active" onClick={() => update({ difficulty: null })}>{query.difficulty} ×</button>}
              {query.status && <button className="pill active" onClick={() => update({ status: null })}>{query.status} ×</button>}
              {query.company && <button className="pill active" onClick={() => update({ company: null, sort: null, order: null })}>{companyName(query.company)} ×</button>}
              {query.tag.map((t) => <button key={t} className="pill active" onClick={() => toggleTag(t)}>{tagName(t)} ×</button>)}
              {query.q && <button className="pill active" onClick={() => { setSearch(''); update({ q: null }) }}>“{query.q}” ×</button>}
              <button className="pill" onClick={() => { setSearch(''); setParams(new URLSearchParams()) }}>Clear all</button>
            </div>
          ) : null}

          {error && <p className="error-text">{error}</p>}
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 40 }}>Status</th>
                  <th className="sortable" onClick={() => setSort('id')}>Title{sortMark('id')}</th>
                  <th className="sortable" onClick={() => setSort('difficulty')} style={{ width: 100 }}>Difficulty{sortMark('difficulty')}</th>
                  <th>Topics</th>
                  {query.company
                    ? <th className="sortable" onClick={() => setSort('frequency')} style={{ width: 110 }}>Frequency{sortMark('frequency')}</th>
                    : <th style={{ width: 90 }}>Companies</th>}
                </tr>
              </thead>
              <tbody>
                {data?.items.map((p) => (
                  <tr key={p.id}>
                    <td><StatusIcon status={p.status} /></td>
                    <td className="title-cell"><Link to={`/problems/${p.slug}`}>{p.frontend_id}. {p.title}</Link></td>
                    <td><DifficultyText value={p.difficulty} /></td>
                    <td className="tags-cell">{p.tags.slice(0, 3).join(', ')}{p.tags.length > 3 ? ` +${p.tags.length - 3}` : ''}</td>
                    <td>
                      {query.company
                        ? <div className="freq-bar" title={`${p.frequency?.toFixed(1)}`}><div style={{ width: `${Math.min(100, p.frequency ?? 0)}%` }} /></div>
                        : <span className="faint">{p.company_count || '—'}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data && data.items.length === 0 && <div className="empty">No problems match these filters.</div>}
            {!data && !error && <div className="empty"><span className="spinner" /></div>}
          </div>

          {data && data.total > 0 && (
            <div className="pagination">
              <span className="muted">{data.total.toLocaleString()} problems</span>
              <div className="pages">
                <button className="btn" disabled={query.page <= 1} onClick={() => update({ page: String(query.page - 1) }, false)}>‹</button>
                {pageWindow(query.page, totalPages).map((n, i) =>
                  n === 0 ? <span key={`gap${i}`} className="faint" style={{ padding: '6px 4px' }}>…</span> : (
                    <button key={n} className={`btn ${n === query.page ? 'current' : ''}`} onClick={() => update({ page: String(n) }, false)}>{n}</button>
                  ))}
                <button className="btn" disabled={query.page >= totalPages} onClick={() => update({ page: String(query.page + 1) }, false)}>›</button>
              </div>
            </div>
          )}
        </section>

        <aside className="sidebar">
          <div className="card">
            <h3>{user ? `Hi, ${user.username}` : 'Track your progress'}</h3>
            {stats ? (
              <div className="diff-rows">
                <div className="diff-row"><span>Solved</span><b>{stats.solved} / {stats.total_problems}</b></div>
                {(['Easy', 'Medium', 'Hard'] as const).map((d) => (
                  <div key={d}>
                    <div className="diff-row"><span className={`diff-${d}`}>{d}</span><span>{stats.by_difficulty[d].solved} / {stats.by_difficulty[d].total}</span></div>
                    <div className="bar"><div style={{ width: `${(100 * stats.by_difficulty[d].solved) / Math.max(1, stats.by_difficulty[d].total)}%`, background: `var(--${d.toLowerCase()})` }} /></div>
                  </div>
                ))}
                <div className="diff-row" style={{ marginTop: 6 }}><span>Current streak</span><b>{stats.streak} day{stats.streak === 1 ? '' : 's'}</b></div>
              </div>
            ) : (
              <p className="muted" style={{ margin: 0 }}>
                <Link to="/register" style={{ color: 'var(--blue)' }}>Create an account</Link> to save solved problems, submissions and your daily streak.
              </p>
            )}
          </div>
          <div className="card">
            <h3>Companies</h3>
            <input className="input" style={{ width: '100%', marginBottom: 10 }} placeholder="Search companies" value={companyQuery} onChange={(e) => setCompanyQuery(e.target.value)} />
            <div className="company-list">
              {filteredCompanies.slice(0, 120).map((c) => (
                <button key={c.slug} className={`pill ${query.company === c.slug ? 'active' : ''}`} onClick={() => update({ company: query.company === c.slug ? null : c.slug, sort: null, order: null })}>
                  {c.name} <span className="count">{c.count}</span>
                </button>
              ))}
            </div>
            <p className="faint" style={{ fontSize: 12, marginBottom: 0 }}>Community-collected company tags, not official LeetCode data.</p>
          </div>
        </aside>
      </div>
    </div>
  )
}

function pageWindow(current: number, total: number): number[] {
  const pages = new Set([1, total, current - 1, current, current + 1, current - 2, current + 2])
  const sorted = [...pages].filter((n) => n >= 1 && n <= total).sort((a, b) => a - b)
  const out: number[] = []
  sorted.forEach((n, i) => {
    if (i && n - sorted[i - 1] > 1) out.push(0)
    out.push(n)
  })
  return out
}
