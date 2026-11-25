import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import Markdown from '../components/Markdown'

export interface Credit { title: string; author: string; repo: string; license: string; license_url: string; notice?: string | null }
export interface BookInfo extends Credit { id: string; chapters: { id: string; title: string }[] }
interface Chapter { id: string; title: string; markdown: string; prev: { id: string; title: string } | null; next: { id: string; title: string } | null; credit: Credit }

export function CreditLine({ c }: { c: Credit }) {
  return (
    <p className="credit">
      From “{c.title}” by {c.author} (<a href={c.repo} target="_blank" rel="noreferrer">source</a>), licensed{' '}
      <a href={c.license_url} target="_blank" rel="noreferrer">{c.license}</a>.{c.notice ? ` ${c.notice}` : ''}
    </p>
  )
}

export function BooksList() {
  const [books, setBooks] = useState<(Credit & { id: string; chapters: number })[] | null>(null)
  useEffect(() => { api.docs().then(setBooks).catch(() => setBooks([])) }, [])
  if (!books) return <span className="spinner" />
  if (books.length === 0) return <p className="muted">Books are not downloaded on this server yet (run <code>python -m scripts.fetch_docs</code>).</p>
  return (
    <div className="card-grid">
      {books.map((b) => (
        <Link key={b.id} to={`/learn/docs/${b.id}`} className="card plan-card">
          <h3>{b.title}</h3><p className="muted">{b.author} · {b.chapters} chapters</p><p className="faint">{b.license}</p>
        </Link>
      ))}
    </div>
  )
}

export function BookPage() {
  const { book = '' } = useParams()
  const [info, setInfo] = useState<BookInfo | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api.book(book).then(setInfo).catch((e: Error) => setError(e.message)) }, [book])
  if (error) return <div className="empty">{error}</div>
  if (!info) return <div className="empty"><span className="spinner" /></div>
  return (
    <div className="container">
      <Link to="/learn?tab=books" className="faint">← Books</Link>
      <h1>{info.title}</h1>
      <CreditLine c={info} />
      <ol className="columns">
        {info.chapters.map((c) => <li key={c.id}><Link to={`/learn/docs/${book}/${c.id}`}>{c.title}</Link></li>)}
      </ol>
    </div>
  )
}

export function ChapterPage() {
  const { book = '', chapter = '' } = useParams()
  const [ch, setCh] = useState<Chapter | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    setCh(null)
    api.chapter(book, chapter).then((c) => { setCh(c); if (!window.location.hash) window.scrollTo(0, 0) }).catch((e: Error) => setError(e.message))
  }, [book, chapter])
  if (error) return <div className="empty">{error}</div>
  if (!ch) return <div className="empty"><span className="spinner" /></div>
  return (
    <div className="container reader">
      <Link to={`/learn/docs/${book}`} className="faint">← {ch.credit.title}</Link>
      <Markdown text={ch.markdown} />
      <div className="reader-nav">
        {ch.prev ? <Link className="btn" to={`/learn/docs/${book}/${ch.prev.id}`}>← {ch.prev.title}</Link> : <span />}
        {ch.next && <Link className="btn" to={`/learn/docs/${book}/${ch.next.id}`}>{ch.next.title} →</Link>}
      </div>
      <CreditLine c={ch.credit} />
    </div>
  )
}
