import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist', 'node_modules'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      // Web Storage can throw in sandboxed iframes: always use src/lib/storage.ts
      'no-restricted-globals': ['error',
        { name: 'localStorage', message: "Use 'local' from src/lib/storage.ts (storage may be blocked)." },
        { name: 'sessionStorage', message: "Use 'session' from src/lib/storage.ts (storage may be blocked)." },
      ],
      'no-restricted-properties': ['error',
        { object: 'window', property: 'localStorage', message: 'Use src/lib/storage.ts' },
        { object: 'window', property: 'sessionStorage', message: 'Use src/lib/storage.ts' },
      ],
    },
  },
  {
    files: ['src/lib/storage.ts', 'tests/**'],
    rules: { 'no-restricted-globals': 'off', 'no-restricted-properties': 'off' },
  },
)
