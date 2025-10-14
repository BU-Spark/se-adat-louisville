// @ts-check

import pluginJs from '@eslint/js';
import tseslint from 'typescript-eslint';
import eslintPluginPrettierRecommended from 'eslint-plugin-prettier/recommended';
import eslintPluginAstro from 'eslint-plugin-astro';

const config = [
  {
    // Global ignores
    ignores: ['.astro/*', 'node_modules/', 'coverage/', 'dist/'],
  },
  {
    // General file settings
    files: ['**/*.{js,mjs,cjs,ts,jsx,tsx,astro}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {},
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
  },
  pluginJs.configs.recommended,
  ...tseslint.configs.recommended,

  {
    // Custom React rules (applied to relevant files)
    files: ['**/*.{jsx,tsx}'],
    rules: {
      'react/prop-types': 'off',
      'react/react-in-jsx-scope': 'off',
    },
  },
  // Astro ESLint plugin recommended config
  ...eslintPluginAstro.configs.recommended,

  // Prettier - applied before Astro overrides
  eslintPluginPrettierRecommended,

  // Override rules specifically for Astro files - MUST be after prettier to take precedence
  {
    files: ['**/*.astro'],
    rules: {
      'prettier/prettier': 'off', // Disable prettier for Astro files to avoid parsing conflicts
      '@typescript-eslint/triple-slash-reference': 'off',
    },
  },
  // Allow TS triple-slash in the canonical Astro env types file
  {
    files: ['src/env.d.ts'],
    rules: {
      '@typescript-eslint/triple-slash-reference': 'off',
    },
  },
];

export default config;
