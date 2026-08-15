// ESLint flat config (ESLint 9).
//
// `npm run lint` was declared in package.json and documented in CLAUDE.md for
// months while being a **phantom command**: eslint was not in devDependencies,
// there was no config file, and ci.yml never invoked it. The third fact explains
// the first two — nothing enforced it, so nobody noticed it did not exist.
//
// The rule this repo should keep: *a quality check that does not run in CI does
// not exist.* It is an intention, not a guarantee. Hence the `lint` job added to
// the workflow alongside this file.
//
// What is deliberately NOT enabled: the type-aware ruleset
// (`recommendedTypeChecked`). It needs a TypeScript program per lint run, which
// is slow, and its highest-value rule for this codebase — no-floating-promises —
// is worth revisiting once the non-typed pass is clean and stays clean.

import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist', 'coverage', 'node_modules'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      // The highest-value rules here. This codebase is full of useCallback and
      // useEffect dependency arrays, and a wrong one produces a stale closure —
      // a bug that compiles, passes types, and surfaces months later as "it
      // sometimes keeps the previous value".
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      // Underscore-prefixed arguments are an intentional "unused on purpose"
      // marker, already used throughout the test doubles.
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },
  {
    // Tests legitimately reach for `any` when shaping mocks against third-party
    // types, and they run in Node globals as well as the browser ones.
    files: ['**/*.test.{ts,tsx}', 'src/test/**'],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
    },
  }
);
