const SOURCES: [string, string, string, string][] = [
  ['LeetCodeDataset', 'https://huggingface.co/datasets/newfacade/LeetCodeDataset', 'Apache-2.0', 'Problem statements, tests, starter code and reference solutions. Downloaded at setup, not stored in the repo.'],
  ['leetcode-company-wise-problems', 'https://github.com/liquidslr/leetcode-company-wise-problems', 'No license (community-collected, unofficial)', 'Company tags and frequency. Downloaded at setup, not stored in the repo.'],
  ['NeetCode', 'https://github.com/neetcode-gh/leetcode', 'MIT', 'Blind 75 and NeetCode roadmap lists (titles, topics).'],
  ["Striver's SDE Sheet", 'https://takeuforward.org/interviews/strivers-sde-sheet-top-coding-interview-problems/', 'Topic order only', 'Our own LeetCode problem selection, inspired by the sheet’s topic order.'],
  ['CrackingTheSQLInterview', 'https://github.com/xoraus/CrackingTheSQLInterview', 'MIT © 2019 Sajjad Salaria', 'SQL interview questions and answers.'],
  ['TheAlgorithms/Python', 'https://github.com/TheAlgorithms/Python', 'MIT', '11 reference implementations in Learn → Templates.'],
  ['Tech Interview Handbook', 'https://github.com/yangshun/tech-interview-handbook', 'MIT © Yangshun Tay', 'Behavioral questions and the full behavioral guide (in-app).'],
  ['System Design Primer', 'https://github.com/donnemartin/system-design-primer', 'CC BY 4.0', 'The full book, read in-app with its images (downloaded at setup).'],
  ['karanpratapsingh/system-design', 'https://github.com/karanpratapsingh/system-design', 'CC BY-NC-ND 4.0', 'The full course, shown verbatim and unmodified, non-commercially, with attribution (downloaded at setup).'],
  ['Pyodide', 'https://pyodide.org', 'MPL-2.0', 'Python in the browser.'],
  ['marked + DOMPurify', 'https://github.com/markedjs/marked', 'MIT / Apache-2.0', 'Rendering the in-app books safely.'],
  ['Monaco Editor', 'https://github.com/microsoft/monaco-editor', 'MIT', 'Code editor.'],
]

export default function SourcesPage() {
  return (
    <div className="container">
      <h1>Sources &amp; licenses</h1>
      <p className="muted">
        CodeArena is free, open source (MIT) and <b>not affiliated with LeetCode</b>. Problem data comes from third-party
        datasets and is downloaded when the server is set up. If you own content here and want it removed, open an issue.
      </p>
      <table className="table">
        <thead><tr><th>Source</th><th>License</th><th>Used for</th></tr></thead>
        <tbody>
          {SOURCES.map(([name, url, lic, use]) => (
            <tr key={name}><td><a href={url} target="_blank" rel="noreferrer">{name}</a></td><td>{lic}</td><td>{use}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
