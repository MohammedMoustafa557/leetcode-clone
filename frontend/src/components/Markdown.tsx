import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { useEffect, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

/** Renders trusted-source markdown safely; in-app links stay in the SPA. */
export default function Markdown({ text }: { text: string }) {
  const html = useMemo(() => {
    const raw = marked.parse(text, { async: false, gfm: true }) as string
    const clean = DOMPurify.sanitize(raw, { ADD_ATTR: ['target'] })
    return clean.replace(/<a href="(https?:)/g, '<a target="_blank" rel="noreferrer" href="$1')
  }, [text])
  const ref = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const onClick = (e: MouseEvent) => {
      const a = (e.target as HTMLElement).closest('a')
      const href = a?.getAttribute('href')
      if (!href) return
      if (href.startsWith('/')) { e.preventDefault(); navigate(href) }
      else if (href.startsWith('#')) {
        e.preventDefault()
        document.getElementById(href.slice(1))?.scrollIntoView({ behavior: 'smooth' })
      }
    }
    el.addEventListener('click', onClick)
    // give headings GitHub-style ids so #anchors work
    el.querySelectorAll('h1,h2,h3,h4,h5,h6').forEach((h) => {
      if (!h.id) h.id = (h.textContent ?? '').trim().toLowerCase().replace(/[^\w\- ]/g, '').replace(/ /g, '-')
    })
    const hash = decodeURIComponent(window.location.hash.slice(1))
    if (hash) document.getElementById(hash)?.scrollIntoView()
    return () => el.removeEventListener('click', onClick)
  }, [html, navigate])

  return <div ref={ref} className="markdown" dangerouslySetInnerHTML={{ __html: html }} />
}
