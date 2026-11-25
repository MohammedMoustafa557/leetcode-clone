import type { ReactNode } from 'react'

// LeetCodeDataset ships statements as plain text with HTML stripped, so exponents
// like 10^4 arrive as "104". Restore the common ones inside the Constraints section.
function restoreExponents(line: string): ReactNode[] {
  // "104" -> 10^4 ... "109" -> 10^9 (values like 100 or 1000 are left alone)
  const parts: ReactNode[] = []
  const re = /(?<![\d.])(-?)10([3-9])(?![\d.])/g
  let last = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(line))) {
    parts.push(line.slice(last, m.index), <span key={`e${m.index}`}>{m[1]}10<sup>{m[2]}</sup></span>)
    last = m.index + m[0].length
  }
  parts.push(line.slice(last))
  return parts
}

function fixPowerOfTwo(line: string): ReactNode[] {
  // "231 - 1" -> 2^31 - 1, "-231" -> -2^31
  const out: ReactNode[] = []
  const re = /(?<![\d.])(-?)2(31|32|63|64)(?![\d.])/g
  let last = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(line))) {
    out.push(line.slice(last, m.index), <span key={`p${m.index}`}>{m[1]}2<sup>{m[2]}</sup></span>)
    last = m.index + m[0].length
  }
  out.push(line.slice(last))
  return out
}

function constraintLine(line: string): ReactNode[] {
  return fixPowerOfTwo(line).flatMap((node) => (typeof node === 'string' ? restoreExponents(node) : [node]))
}

export default function Description({ text }: { text: string }) {
  const lines = text.split('\n')
  const blocks: ReactNode[] = []
  let i = 0
  let section: 'body' | 'constraints' = 'body'
  let key = 0

  while (i < lines.length) {
    const line = lines[i].trim()
    if (!line) { i++; continue }
    if (/^Example \d+:?$/.test(line)) {
      const ex: string[] = []
      i++
      while (i < lines.length && !/^(Example \d+:?|Constraints:|Follow[- ]?up)/.test(lines[i].trim())) {
        if (lines[i].trim()) ex.push(lines[i].trim())
        i++
      }
      blocks.push(<h4 key={key++}>{line.replace(/:?$/, ':')}</h4>)
      blocks.push(
        <div className="example" key={key++}>
          {ex.map((l, j) => {
            const m = l.match(/^(Input|Output|Explanation):\s?(.*)$/)
            return <div key={j}>{m ? <><b>{m[1]}:</b> {m[2]}</> : l}</div>
          })}
        </div>,
      )
      continue
    }
    if (/^Constraints:?$/.test(line)) {
      section = 'constraints'
      blocks.push(<h4 key={key++}>Constraints:</h4>)
      const items: string[] = []
      i++
      while (i < lines.length && !/^Follow[- ]?up/i.test(lines[i].trim())) {
        if (lines[i].trim()) items.push(lines[i].trim())
        i++
      }
      blocks.push(<ul key={key++}>{items.map((it, j) => <li key={j}><code>{constraintLine(it)}</code></li>)}</ul>)
      continue
    }
    if (/^Follow[- ]?up/i.test(line)) {
      const rest = line.replace(/^Follow[- ]?up:?\s*/i, '')
      blocks.push(<p key={key++}><b>Follow-up:</b> {section === 'constraints' ? constraintLine(rest) : rest}</p>)
      i++
      continue
    }
    blocks.push(<p key={key++}>{line}</p>)
    i++
  }
  return <div className="desc">{blocks}</div>
}
