import js from '@eslint/js'
import ts from 'typescript-eslint'

export default ts.config(
  { ignores: ['dist/**', 'release/**', 'playwright-report/**', 'test-results/**', '.venv*/**', '.local/**', 'public/vision/**'] },
  { files: ['**/*.{js,mjs,cjs}'], ...js.configs.recommended },
  ...ts.configs.recommended,
  { files: ['public/audio/*.js'], languageOptions: { globals: {
    AudioWorkletProcessor: 'readonly', registerProcessor: 'readonly', currentTime: 'readonly',
  } } },
  { files: ['electron/*.cjs'], rules: { '@typescript-eslint/no-require-imports': 'off' }, languageOptions: { globals: {
    require: 'readonly', process: 'readonly', __dirname: 'readonly', console: 'readonly',
    URL: 'readonly', Response: 'readonly', Headers: 'readonly',
  } } },
)
