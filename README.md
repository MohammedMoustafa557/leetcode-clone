 a LeetCode-style practice platform

[![CI](https://github.com/MohammedMoustafa557/leetcode-clone/actions/workflows/ci.yml/badge.svg)](https://github.com/MohammedMoustafa557/leetcode-clone/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688) ![React](https://img.shields.io/badge/React-19-61dafb) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791) ![License](https://img.shields.io/badge/license-MIT-green)

A full-stack coding-interview practice site. It has **2,869 real interview problems** at every difficulty, which you can filter by **topic (63 tags)** and **company (415 companies)**. You write Python in a Monaco editor and run it **inside your browser** against hundreds of hidden test cases. Your progress, submissions and daily streak are saved to your account.

## Features

- **Problem catalog.** 2,869 problems (686 Easy / 1,498 Medium / 685 Hard) with statements, examples, constraints and starter code.
- **Filters like LeetCode.** Search by title or number. Filter by difficulty, by one or more topics (AND), by company and by status (todo / attempted / solved). You can sort by number, title, difficulty or company frequency, and **Pick one** opens a random unsolved problem.
- **Company tags.** 14,193 problem-company links with frequency and recency ("asked in the last 30 days", and so on).
- **In-browser judge.** Python 3.12 runs in [Pyodide](https://pyodide.org) (CPython compiled to WebAssembly) inside a Web Worker:
  - **Run** checks your code against the first 3 test cases and shows input, output and expected output for each one.
  - **Submit** runs the full hidden suite, about 100 cases on average. The verdict is **Accepted**, **Wrong Answer**, **Runtime Error** (with the line number), **Compile Error** or **Time Limit Exceeded**. A runaway loop is stopped by killing the worker.
  - `print()` output is captured and shown as stdout.
- **Accounts.** Register and log in with a username or email. Passwords are hashed with bcrypt, sessions use JWT bearer tokens, and the API also supports the OAuth2 password flow (the Swagger "Authorize" button).
- **Progress tracking.** Each problem gets a solved or attempted status, and you get a submission history with the code of every attempt. There are per-difficulty progress bars, current and longest **streak**, acceptance rate, a year-long activity heatmap and your strongest topics.
- **Study plans.** Blind 75 (68 of 75 in the catalog), the NeetCode roadmap (378 of 450, 18 topics) and a Striver-style SDE sheet (131 problems, 26 topics), each with your progress. A **problem of the day** rotates through the NeetCode topics by date.
- **Per-problem guide.** 3 progressive hints, a simple-English explanation, time/space complexity and 5 interview sentences with Arabic translations. Without an AI key everything is *derived* from the tags and an AST scan of the reference solution (labelled as estimated). With `LLM_API_KEY` set, an OpenAI-compatible model writes it, and it is cached in the database.
- **45-minute mock interviews.** Pick a company, get 2 real problems it asks, a countdown timer on the problem page and a score.
- **Weekly contest.** 4 problems (Easy, Medium, Medium, Hard), a fixed 90-minute window every Friday (16:00 UTC by default), live standings with LeetCode-style penalty time, and a multi-player **Elo rating** update when it ends.
- **Dashboard, leaderboard and badges.** Public profiles with Easy/Medium/Hard rings, points, contest rating, global rank, contest history and 10 badges. The leaderboard ranks everyone by points, streak or rating.
- **Stats.** 26-week activity heatmap and per-topic strengths and weaknesses (accuracy per tag).
- **Learn, all inside the site.** 16 coding patterns with templates and linked problems, 11 Python algorithm templates (TheAlgorithms), 115 SQL interview Q&As, 117 behavioral questions with STAR guidance, and three full books you read in-app with their images: *The System Design Primer*, Karan Pratap Singh's *System Design* course and the Tech Interview Handbook's behavioral guide.
- **Optional Notion sync.** First-time solves of one configured user are added to a Notion database (off by default).
- **Workspace niceties.** You get a resizable split view, autosaved drafts for each problem, font size control, Ctrl+' to run and Ctrl+Enter to submit, a reference solution tab and a dark/light theme.

## Architecture

```mermaid
flowchart LR
  subgraph Browser
    UI[React + Vite + TypeScript] -->|postMessage| W[Web Worker]
    W --> P[Pyodide: CPython in WASM]
    P --> H[runner/harness.py]
  end
  UI -->|REST + JWT| API[FastAPI]
  API --> DB[(PostgreSQL)]
  Seed[scripts/seed.py] -->|download| HF[LeetCodeDataset on Hugging Face]
  Seed -->|download| GH[company-wise CSVs on GitHub]
  Seed --> DB
```

```
.
├── backend/                 FastAPI + SQLAlchemy 2 + Alembic
│   ├── app/api/             auth, problems, submissions/stats routers
│   ├── app/models/          User, Problem, Tag, Company, ProblemCompany, Submission
│   ├── app/services/        progress + streak logic
│   ├── alembic/versions/    migrations
│   ├── scripts/seed.py      downloads + loads all problems and company tags
│   ├── scripts/validate_dataset.py   judges every reference solution
│   └── tests/               pytest (API, auth, seed, judge harness)
├── runner/harness.py        the judge, shared by the browser and the tests
├── frontend/                React 19 + Vite + TypeScript + Monaco
│   ├── src/runner/          Pyodide worker, judge client with timeouts
│   ├── src/pages/           Problems, Problem workspace, Auth, Progress
│   └── scripts/judge-smoke.ts   runs the real Pyodide judge in Node
├── docker-compose.yml       db + backend + frontend (nginx)
└── .github/workflows/ci.yml
```

### How judging works

Every problem in LeetCodeDataset has a test function with one `assert` per test case:

```python
def check(candidate):
    assert candidate(nums = [3, 3], target = 6) == [0, 1]
    ...
```

`runner/harness.py` parses this with `ast` and runs each assert as its own case, so it can report *which* case failed and show `output` next to `expected`. A fresh `Solution()` is created for every case. It defines the same helpers LeetCode provides (`ListNode`, `TreeNode`, `list_node`, `tree_node`, …), and it maps exceptions to a line in *your* code.

The same file runs in two places:

- **in the browser**, inside Pyodide in a Web Worker, so user code never runs on the server;
- **in CI**, under CPython (`pytest`) and under real Pyodide in Node (`npm run test:judge`).

> **Trust model.** Verdicts are computed on the client and then reported to the API. The API checks them (an "Accepted" result must pass every test of that problem), but a determined user could still fake a submission. That is fine for a personal practice tool. A server-side sandboxed judge is listed under Roadmap below.

## Getting started

### With Docker (recommended)

```bash
cp .env.example .env          # then set JWT_SECRET and POSTGRES_PASSWORD
docker compose up --build
```

Open <http://localhost:8080>. API docs are at <http://localhost:8000/docs>.
On first start the backend runs migrations and downloads about 100 MB of public data, then seeds all problems. This takes about a minute and is cached in a volume after that.

### Local development

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://leetcode:leetcode@localhost:5432/leetcode JWT_SECRET=dev
alembic upgrade head
python -m scripts.seed            # or: --limit 100 for a quick seed
uvicorn app.main:app --reload     # http://localhost:8000/docs

# frontend (in another terminal)
cd frontend
npm install
npm run dev                       # http://localhost:5173 (proxies /api to :8000)
```

No PostgreSQL? Use SQLite instead: `DATABASE_URL=sqlite:///./dev.db python -m scripts.seed --create-tables`.

**Offline Python runtime.** Pyodide loads from the jsDelivr CDN by default. To self-host it, run `npm run pyodide:local` and build with `VITE_PYODIDE_URL=/pyodide/`.

### Tests

```bash
cd backend && pytest                    # 54 tests, SQLite, fully offline
TEST_DATABASE_URL=postgresql+psycopg://... pytest   # same suite on PostgreSQL
ruff check . ../runner

cd frontend && npm run lint && npm run test:unit && npm run build
npm run test:judge                      # real Pyodide: Accepted / Wrong Answer / errors
```

CI runs all of the above on every push. It also runs a Postgres job that migrates, seeds 200 problems and smoke-tests the API.

## API overview

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/auth/register` | Create an account and return a JWT |
| POST | `/api/auth/login` | Log in with username or email |
| GET | `/api/auth/me` | Current user |
| GET | `/api/problems` | List problems with `q`, `difficulty`, `tag` (repeatable), `company`, `status`, `sort`, `order`, `page`, `page_size` |
| GET | `/api/problems/random` | Random problem (unsolved first) |
| GET | `/api/problems/{slug}` | Statement, starter code, tests, companies |
| GET | `/api/problems/{slug}/solution` | Reference solution |
| GET | `/api/tags`, `/api/companies` | Facets with counts |
| POST | `/api/submissions` | Record a judged submission |
| GET | `/api/submissions` | Your submission history (`problem_slug` filter) |
| GET | `/api/me/stats` | Solved per difficulty, streaks, heatmap, per-topic strengths and weaknesses |
| GET | `/api/plans`, `/api/plans/{id}` | Study plans (`blind75`, `neetcode`, `striver`) with your progress |
| GET | `/api/daily` | Problem of the day |
| GET | `/api/problems/{slug}/guide` | Hints, explanation, complexity, interview sentences |
| GET | `/api/learn/{patterns,templates,sql,behavioral,system-design}` | Learn content |
| GET | `/api/docs`, `/api/docs/{book}`, `/api/docs/{book}/{chapter}` | In-app books (markdown + images) |
| POST/GET | `/api/interviews`, `/api/interviews/{id}`, `/api/interviews/{id}/finish` | Mock interviews |
| GET | `/api/contests/current`, `/api/contests/{n}`; POST `/api/contests/{n}/register` | Weekly contests |
| GET | `/api/leaderboard?sort=points\|streak\|rating`, `/api/users/{username}` | Leaderboard, public dashboard |

Interactive docs: `http://localhost:8000/docs` (Swagger) and `/redoc`.

## Data quality notes

- `scripts/validate_dataset.py` ran every reference solution against its full test suite (CPython, 20 s and 1 GB limit per problem). **2,829 of 2,869 (98.6%) were Accepted.** The other 40 have extremely heavy test suites. They are listed in `backend/scripts/heavy_problems.json` and flagged in the UI, which gives them a 30 s time limit instead of 10 s.
- The dataset strips HTML from statements, so `10⁴` arrives as `104`. The UI restores common exponents in the Constraints section, but a few statements may still read oddly.
- The dataset has no titles, so titles come from the company CSVs (2,649 problems). The rest are generated from the slug.
- Company tags are **community-collected and unofficial**. They are not LeetCode's own data.

## Data credits and disclaimer

**CodeArena is not affiliated with, endorsed by or connected to LeetCode.** LeetCode is a trademark of LeetCode LLC.
Problem statements belong to their owners. They are **not stored in this repository**: the seed script downloads them at setup
time from the public [LeetCodeDataset](https://huggingface.co/datasets/newfacade/LeetCodeDataset) (Apache-2.0). The same is
true for company tags ([liquidslr/leetcode-company-wise-problems](https://github.com/liquidslr/leetcode-company-wise-problems),
no license, community-collected and unofficial) and for the books in Learn (`python -m scripts.fetch_docs`).
If you own any of this content and want it removed, please open an issue and it will be taken down.

Every source and its license is listed in [SOURCES.md](SOURCES.md) and on the in-app **Sources** page.

## Roadmap

- [ ] Server-side multi-language judge (Python, JavaScript, Java, C++) in a sandbox (self-hosted Judge0 or Piston), Pyodide kept as offline fallback; runtime/memory percentiles
- [ ] Discussions, shared solutions with upvotes, editorials, follows, submission diffs
- [ ] Virtual contests, Glicko-2 ratings, streak freeze
- [ ] Spaced-repetition review queue, Arabic UI (RTL), PWA, admin panel, OAuth login, rate limiting

## License

[MIT](LICENSE) © 2026 Mohammed Moustafa
