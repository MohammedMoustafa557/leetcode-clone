// Copies the Pyodide runtime from node_modules into public/pyodide so the app can
// run Python without reaching a CDN. Build with VITE_PYODIDE_URL=/pyodide/ afterwards.
import { cpSync, mkdirSync, readdirSync } from 'node:fs'

const src = new URL('../node_modules/pyodide/', import.meta.url)
const dest = new URL('../public/pyodide/', import.meta.url)
mkdirSync(dest, { recursive: true })
for (const f of readdirSync(src)) {
  if (/\.(mjs|js|wasm|zip|json)$/.test(f) && f !== 'package.json') cpSync(new URL(f, src), new URL(f, dest))
}
console.log('Pyodide copied to public/pyodide/')
