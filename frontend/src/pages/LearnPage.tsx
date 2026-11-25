import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type { BriefProblem } from '../api/types'
import ProblemLink from '../components/ProblemLink'
import { BooksList, type BookInfo } from './DocsPages'

interface Pattern { name: string; when: string; idea: string; template: string; problems: BriefProblem[] }
interface SqlQA { source: string; license: string; questions: { number: number; section: string; question: string; answer: string }[] }
interface Templates { source: string; license: string; templates: { title: string; tag: string; url: string; code: string }[] }
interface Behavioral { source: string; repo: string; license: string; sections: { title: string; questions: string[] }[] }
interface SystemDesign {
  primer: { source: string; license: string; topics: { title: string; url: string }[] }
  karan: { source: string; license: string; chapters: { title: string; url: string }[] }
}

const TABS = [
  ['patterns', 'Patterns'], ['books', 'Books'], ['templates', 'Templates'], ['sql', 'SQL'], ['behavioral', 'Behavioral'], ['system-design', 'System Design'],
] as const
type Tab = (typeof TABS)[number][0]

function useSection<T>(tab: Tab) {
  const [data, setData] = useState<T | null>(null)
  useEffect(() => { setData(null); api.learn<T>(tab as Exclude<Tab, 'books'>).then(setData).catch(() => {}) }, [tab])
  return data
}

function Patterns() {
  const data = useSection<Pattern[]>('patterns')
  if (!data) return <span className="spinner" />
  return <>{data.map((p) => (
    <details key={p.name} className="card plan-group">
      <summary><b>{p.name}</b> <span className="faint">{p.problems.length} problems</span></summary>
      <p><b>When:</b> {p.when}</p>
      <p><b>Idea:</b> {p.idea}</p>
      <pre className="io-box">{p.template}</pre>
      {p.problems.map((x) => <ProblemLink key={x.slug} p={x} />)}
    </details>
  ))}</>
}

function TemplatesTab() {
  const data = useSection<Templates>('templates')
  if (!data) return <span className="spinner" />
  return <>
    <p className="faint">From <a href={data.source} target="_blank" rel="noreferrer">TheAlgorithms/Python</a> ({data.license}).</p>
    {data.templates.map((t) => (
      <details key={t.title} className="card plan-group">
        <summary><b>{t.title}</b></summary>
        <pre className="io-box code-scroll">{t.code}</pre>
        <p className="credit">Source: TheAlgorithms/Python, <code>{t.url.split('/blob/master/')[1]}</code> (MIT).</p>
        <Link to={`/problems?tag=${t.tag}`}>Practice {t.tag} problems →</Link>
      </details>
    ))}
  </>
}

function Sql() {
  const data = useSection<SqlQA>('sql')
  const [q, setQ] = useState('')
  if (!data) return <span className="spinner" />
  const list = data.questions.filter((x) => (x.question + x.answer).toLowerCase().includes(q.toLowerCase()))
  let last = ''
  return <>
    <p className="faint">{data.questions.length} questions from <a href={data.source} target="_blank" rel="noreferrer">CrackingTheSQLInterview</a> ({data.license}).</p>
    <input className="input" placeholder="Search SQL questions" value={q} onChange={(e) => setQ(e.target.value)} />
    {list.map((x) => {
      const head = x.section !== last ? <h3 key={`h${x.number}`}>{(last = x.section)}</h3> : null
      return <div key={x.number}>{head}
        <details className="card plan-group"><summary>{x.number}. {x.question}</summary><pre className="io-box answer">{x.answer}</pre></details>
      </div>
    })}
  </>
}

function BehavioralTab() {
  const data = useSection<Behavioral>('behavioral')
  if (!data) return <span className="spinner" />
  const total = data.sections.reduce((n, s) => n + s.questions.length, 0)
  return <>
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Answer with STAR</h3>
      <ul>
        <li><b>Situation</b> – one or two sentences of context: "In my last project, our API was too slow."</li>
        <li><b>Task</b> – what <i>you</i> had to do: "I had to cut the response time in half."</li>
        <li><b>Action</b> – the steps you took, using "I": "I profiled the endpoints and added caching."</li>
        <li><b>Result</b> – a number if possible: "Response time went from 800 ms to 300 ms."</li>
      </ul>
      <p className="faint">Keep each answer around 2 minutes. Prepare 5–6 stories you can reuse for many questions.</p>
    </div>
    <p className="faint">{total} questions in {data.sections.length} sections from the Tech Interview Handbook ({data.license}). Read the full guide in <Link to="/learn/docs/behavioral-handbook">Books → Behavioral Interviews</Link>.</p>
    {data.sections.map((s) => (
      <details key={s.title} className="card plan-group">
        <summary><b>{s.title}</b> <span className="faint">{s.questions.length}</span></summary>
        <ol>{s.questions.map((q) => <li key={q}>{q}</li>)}</ol>
      </details>
    ))}
  </>
}

function SystemDesignTab() {
  const data = useSection<SystemDesign>('system-design')
  const [books, setBooks] = useState<BookInfo[]>([])
  useEffect(() => {
    Promise.all(['system-design-primer', 'karan-system-design'].map((id) => api.book(id).catch(() => null)))
      .then((r) => setBooks(r.filter((b): b is BookInfo => b !== null)))
  }, [])
  if (!data) return <span className="spinner" />
  return <>
    <div className="card">
      <h3 style={{ marginTop: 0 }}>How to approach a design question</h3>
      <ol>
        <li>Ask about use cases, users and scale (requests per second, data size).</li>
        <li>Draw the high-level design: clients, load balancer, services, database, cache.</li>
        <li>Go deeper on the core parts: data model, APIs, the hardest component.</li>
        <li>Scale it: replication, sharding, caching, queues. Name the trade-offs.</li>
      </ol>
    </div>
    {books.map((b) => (
      <div key={b.id}>
        <h3>{b.title} <span className="faint" style={{ fontWeight: 400, fontSize: 13 }}>· {b.chapters.length} chapters · {b.license}</span></h3>
        <ol className="columns">{b.chapters.map((c) => <li key={c.id}><Link to={`/learn/docs/${b.id}/${c.id}`}>{c.title}</Link></li>)}</ol>
      </div>
    ))}
    {books.length === 0 && <p className="muted">The system design books are not downloaded on this server yet. Topics: {data.primer.topics.map((t) => t.title).join(', ')}.</p>}
  </>
}

export default function LearnPage() {
  const [params, setParams] = useSearchParams()
  const tab = (params.get('tab') as Tab) || 'patterns'
  return (
    <div className="container">
      <h1>Learn</h1>
      <div className="tabs">
        {TABS.map(([id, label]) => (
          <button key={id} className={`tab ${tab === id ? 'active' : ''}`} onClick={() => setParams({ tab: id })}>{label}</button>
        ))}
      </div>
      <div style={{ marginTop: 16 }}>
        {tab === 'patterns' && <Patterns />}
        {tab === 'books' && <BooksList />}
        {tab === 'templates' && <TemplatesTab />}
        {tab === 'sql' && <Sql />}
        {tab === 'behavioral' && <BehavioralTab />}
        {tab === 'system-design' && <SystemDesignTab />}
      </div>
      <p className="faint" style={{ marginTop: 24 }}>See <Link to="/sources">Sources &amp; licenses</Link> for credits.</p>
    </div>
  )
}
