# Sources and licenses

The MIT license in `LICENSE` covers the source code of this repository only. Third-party content keeps its own license.

| Source | Used for | License | In the repo? |
| --- | --- | --- | --- |
| [LeetCodeDataset](https://huggingface.co/datasets/newfacade/LeetCodeDataset) (newfacade) | Problem statements, starter code, tests, reference solutions | Apache-2.0 | **No.** Downloaded by `backend/scripts/seed.py` at setup. The test fixture keeps only code/tests for 6 problems, with our own one-line descriptions. |
| [leetcode-company-wise-problems](https://github.com/liquidslr/leetcode-company-wise-problems) (liquidslr) | Company tags, frequency, recency | No license file | **No.** Downloaded at setup. Community-collected and unofficial. |
| [neetcode-gh/leetcode](https://github.com/neetcode-gh/leetcode) | Blind 75 / NeetCode roadmap lists (titles, slugs, topics) | MIT | Yes: `backend/app/content/neetcode.json` |
| [Striver's SDE Sheet](https://takeuforward.org/interviews/strivers-sde-sheet-top-coding-interview-problems/) | Topic order of our own SDE sheet | — (our own selection) | Yes: `striver_sde.json` (slugs only) |
| [xoraus/CrackingTheSQLInterview](https://github.com/xoraus/CrackingTheSQLInterview) | 115 SQL interview Q&As | MIT, © 2019 Sajjad Salaria | Yes: `sql_qa.json` |
| [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | 11 algorithm templates (full source) | MIT | Yes: `templates.json` |
| [yangshun/tech-interview-handbook](https://github.com/yangshun/tech-interview-handbook) | Behavioral questions (`behavioral.json`) and the behavioral guide (in-app book) | MIT, © Yangshun Tay | Questions yes; the guide is downloaded at setup |
| [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | The System Design Primer (in-app book, with images) | CC BY 4.0 | **No.** Downloaded by `scripts/fetch_docs.py`; only chapter split, image and anchor URLs are adapted for display |
| [karanpratapsingh/system-design](https://github.com/karanpratapsingh/system-design) | System Design course (in-app book, with images) | CC BY-NC-ND 4.0 | **No.** Downloaded at setup and shown verbatim and unmodified, non-commercially, with attribution and the license notice on every page |
| [Pyodide](https://pyodide.org) | CPython in WebAssembly | MPL-2.0 | npm dependency / CDN |
| [Monaco Editor](https://github.com/microsoft/monaco-editor) | Code editor | MIT | npm dependency |
| [marked](https://github.com/markedjs/marked), [DOMPurify](https://github.com/cure53/DOMPurify) | Markdown rendering and sanitising | MIT; Apache-2.0 or MPL-2.0 | npm dependencies |

The 16 coding-pattern write-ups, hints and interview sentences are original to this project (MIT).

LeetCode is a trademark of LeetCode LLC. This project is independent and not affiliated with or endorsed by LeetCode. To request removal of any content, open an issue.
