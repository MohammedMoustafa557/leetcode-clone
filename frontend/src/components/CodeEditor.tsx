import Editor, { loader, type OnMount } from '@monaco-editor/react'
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api'
import 'monaco-editor/esm/vs/basic-languages/python/python.contribution'
import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'

// Bundle Monaco locally instead of loading it from a CDN.
self.MonacoEnvironment = { getWorker: () => new EditorWorker() }
loader.config({ monaco })

interface Props {
  value: string
  onChange: (v: string) => void
  onRun: () => void
  onSubmit: () => void
  fontSize: number
}

export default function CodeEditor({ value, onChange, onRun, onSubmit, fontSize }: Props) {
  const handleMount: OnMount = (editor, m) => {
    editor.addCommand(m.KeyMod.CtrlCmd | m.KeyCode.Quote, onRun)
    editor.addCommand(m.KeyMod.CtrlCmd | m.KeyCode.Enter, onSubmit)
  }
  const theme = document.documentElement.dataset.theme === 'light' ? 'vs' : 'vs-dark'
  return (
    <Editor
      language="python"
      theme={theme}
      value={value}
      onChange={(v) => onChange(v ?? '')}
      onMount={handleMount}
      options={{
        fontSize,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        tabSize: 4,
        automaticLayout: true,
        fontFamily: "'JetBrains Mono', 'Fira Code', Menlo, Consolas, monospace",
        padding: { top: 10 },
      }}
    />
  )
}
