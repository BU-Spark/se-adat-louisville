<<<<<<< HEAD
# Astro Starter Kit: Basics

```sh
npm create astro@latest -- --template basics
```

> 🧑‍🚀 **Seasoned astronaut?** Delete this file. Have fun!

## 🚀 Project Structure

Inside of your Astro project, you'll see the following folders and files:

```text
/
├── public/
│   └── favicon.svg
├── src
│   ├── assets
│   │   └── astro.svg
│   ├── components
│   │   └── Welcome.astro
│   ├── layouts
│   │   └── Layout.astro
│   └── pages
│       └── index.astro
└── package.json
```

To learn more about the folder structure of an Astro project, refer to [our guide on project structure](https://docs.astro.build/en/basics/project-structure/).

## 🧞 Commands

All commands are run from the root of the project, from a terminal:

| Command                   | Action                                           |
| :------------------------ | :----------------------------------------------- |
| `npm install`             | Installs dependencies                            |
| `npm run dev`             | Starts local dev server at `localhost:4321`      |
| `npm run build`           | Build your production site to `./dist/`          |
| `npm run preview`         | Preview your build locally, before deploying     |
| `npm run astro ...`       | Run CLI commands like `astro add`, `astro check` |
| `npm run astro -- --help` | Get help using the Astro CLI                     |

## 👀 Want to learn more?

Feel free to check [our documentation](https://docs.astro.build) or jump into our [Discord server](https://astro.build/chat).
=======
This is a template for Spark! DS 519 projects. It ships with an Astro 5 + React 19 islands stack, along with eslint.config.mjs ([`ESLint`](https://eslint.org/)) and .prettierrc ([`Prettier`](https://prettier.io/)) aligned to industry-standard guidelines.

## Setting Up Your Developer Experience

To get the most out of the linting and formatting workflow, make these IDE changes:

#### Add this code to your _.vscode/settings.json_

```json
{
  "editor.formatOnSave": true,
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

#### Download these VSCode extensions:

- [ESLint](https://marketplace.visualstudio.com/items?itemName=dbaeumer.vscode-eslint)
- [Prettier](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode)

## Getting Started

This template uses [Astro](https://docs.astro.build/) with React components mounted as islands.

1. Install dependencies
   ```bash
   npm install
   ```
2. Start the dev server
   ```bash
   npm run dev
   ```
3. Open [http://localhost:4321](http://localhost:4321) in your browser. Astro will hot-reload when you edit files such as `src/pages/index.astro` or any component under `src/components/`.

### Useful npm scripts

- `npm run build` – type-checks with `astro check` and produces a static build in `dist/`.
- `npm run preview` – serves the production build locally.
- `npm run lint` – runs ESLint and Prettier on the project.
- `npm run test` – executes the Vitest suite.

## Testing Your Application

This template includes a Vitest + React Testing Library stack so you can cover Astro islands and utility code.

<details>
  <summary><strong>Key Testing Features & Configuration</strong></summary>

#### Integrated Tools

- **Vitest:** Fast test runner compatible with Vite/Astro projects.
- **React Testing Library (RTL):** User-centric utilities for rendering and asserting against React components.
- **`@testing-library/jest-dom`:** Extends Vitest/Jest matchers with DOM-specific assertions such as `toBeInTheDocument`.

#### Configuration Files

- **`vitest.config.ts`:** Core Vitest configuration. Sets up jsdom, aliases (`@/` and `~/`), and pulls in the Astro + React plugins.
- **`vitest.setup.ts`:** Loaded before every test; registers RTL helpers and custom matchers.

#### Test File Location

- Co-locate tests with the code they cover (e.g., `Button.test.tsx` next to `Button.tsx`). Vitest is configured to pick up `*.test.{ts,tsx}` files.

</details>

<details>
  <summary><strong>Running Tests</strong></summary>

- **`npm test`**: Runs the full test suite once. (Used by Husky hooks.)
  ```bash
  npm test
  ```
- **`npm run test:watch`**: Re-runs affected tests on file change.
  ```bash
  npm run test:watch
  ```
- **`npm run test:coverage`**: Generates coverage reports in `coverage/`.
  ```bash
  npm run test:coverage
  ```
  </details>

<details>
  <summary><strong>Automated Testing with Husky</strong></summary>

To safeguard quality, Husky manages Git hooks:

- **`pre-commit`**: Executes `npx lint-staged` to lint/format staged files before committing.
- **`pre-push`**: Runs `npm test` to verify the suite before pushing.

Fix any issues surfaced by these hooks prior to completing your Git action.

</details>

<details>
  <summary><strong>Testing Philosophy</strong></summary>

- **Focus on User Behavior:** Prefer interactions that mirror how someone uses the UI rather than reaching into component internals.
- **Unit & Integration Coverage:** Mix small targeted tests with broader flows that stitch together multiple islands/utilities.
- **Confidence over Metrics:** Use coverage to spot gaps, but prioritize scenarios that protect critical behavior.
- **Readable Tests:** Keep assertions clear and avoid brittle selectors to make the suite easy to maintain.
</details>

## Managing Environment Variables

Astro loads environment variables from `.env` files using Vite conventions.

- **Local secrets:** Store them in `.env` or `.env.local` (already in `.gitignore`) for values that should never leave your machine.
- **Expose to the client:** Prefix variables with `PUBLIC_` (e.g., `PUBLIC_ANALYTICS_ID`). Access via `import.meta.env.PUBLIC_ANALYTICS_ID`.
- **Server-only values:** Variables without the `PUBLIC_` prefix are only available in server-side code (Astro endpoints, server-only utilities).
- **Provide a template:** Commit an `.env.example` with placeholder values so teammates know which settings to configure.

See the [Astro docs on environment variables](https://docs.astro.build/en/guides/environment-variables/) for deeper control, including runtime vs. build-time values.

## Adding Additional Tech

Astro is flexible and supports many integrations. A few starting points:

- [Astro Integrations](https://docs.astro.build/en/guides/integrations-guide/) – official and community packages (Tailwind, MDX, image optimizers, adapters).
- [Content Collections](https://docs.astro.build/en/guides/content-collections/) – typed content authoring for blogs, docs, or marketing pages.
- [SSR & Adapters](https://docs.astro.build/en/guides/server-side-rendering/) – switch from static output to SSR if your deployment needs it.
- [React Ecosystem](https://docs.astro.build/en/guides/integrations-guide/react/) – guidance on using React libraries within Astro islands.

### Component Libraries
All new projects are expected to align with a design system. Work with your DS488 design team to determine the component library (e.g., Material UI, Chakra UI, Tailwind UI) that best matches the provided design kit, then integrate it within Astro/React islands.
>>>>>>> origin/feature/LandingPage-rb
