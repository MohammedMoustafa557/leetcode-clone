// End-to-end check of the judge with the *real* runtime: Pyodide (WebAssembly CPython) in Node.
// It loads runner/harness.py exactly like the browser worker does, then judges sample
// problems with the reference solution (must be Accepted) and a wrong one (must be Wrong Answer).
//
//   npm run test:judge
import { readFileSync } from 'node:fs'
import { loadPyodide } from 'pyodide'
import { JSON_HELPERS } from '../src/runner/protocol.ts'

interface Sample { task_id: string; prompt: string; completion: string; entry_point: string; test: string }

const root = new URL('../../', import.meta.url)
const harness = readFileSync(new URL('runner/harness.py', root), 'utf8')
const samples: Sample[] = JSON.parse(readFileSync(new URL('backend/tests/fixtures/sample_problems.json', root), 'utf8'))

const WRONG: Record<string, string> = {
  'two-sum': 'class Solution:\n    def twoSum(self, nums, target):\n        return [0, 1]\n',
  'valid-parentheses': 'class Solution:\n    def isValid(self, s):\n        return len(s) % 2 == 0\n',
  'reverse-linked-list': 'class Solution:\n    def reverseList(self, head):\n        return head\n',
  'maximum-depth-of-binary-tree': 'class Solution:\n    def maxDepth(self, root):\n        return 1 if root else 0\n',
  'climbing-stairs': 'class Solution:\n    def climbStairs(self, n):\n        return n\n',
  'number-of-islands': 'class Solution:\n    def numIslands(self, grid):\n        return 1\n',
}

const py = await loadPyodide()
py.runPython(harness)
py.runPython(JSON_HELPERS)
const runJson = py.globals.get('run_json')

let failures = 0
const check = (label: string, got: string, want: string, detail = '') => {
  const ok = got === want
  if (!ok) failures++
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label.padEnd(48)} -> ${got}${detail}`)
}

for (const s of samples) {
  const good = JSON.parse(runJson(s.prompt, s.completion, s.entry_point, s.test, null))
  check(`${s.task_id} (reference solution)`, good.verdict, 'Accepted', ` ${good.passed}/${good.total}`)
  const bad = JSON.parse(runJson(s.prompt, WRONG[s.task_id], s.entry_point, s.test, null))
  check(`${s.task_id} (wrong solution)`, bad.verdict, 'Wrong Answer', ` ${bad.passed}/${bad.total}`)
}
const ts = samples[0]
const rt = JSON.parse(runJson(ts.prompt, 'class Solution:\n    def twoSum(self, nums, target):\n        return nums[10**6]\n', ts.entry_point, ts.test, null))
check('two-sum (index error)', rt.verdict, 'Runtime Error')
const ce = JSON.parse(runJson(ts.prompt, 'class Solution(:\n', ts.entry_point, ts.test, null))
check('two-sum (syntax error)', ce.verdict, 'Compile Error')
const run3 = JSON.parse(runJson(ts.prompt, ts.completion, ts.entry_point, ts.test, 3))
check('two-sum (Run = first 3 cases)', `${run3.verdict} ${run3.total}`, 'Accepted 3')

console.log(failures ? `\n${failures} check(s) failed` : '\nAll judge checks passed')
process.exit(failures ? 1 : 0)
