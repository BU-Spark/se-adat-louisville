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

## Adding Google Maps API Key

A google maps API key is needed from Google Cloud Console. Follow the steps in the guide below and insert your key in '.env' under PUBLIC_GOOGLE_MAPS_API_KEY. Make sure Maps, Autocomplete, and Geocoding are toggled on for your API key.

(https://developers.google.com/maps/documentation/javascript/get-api-key)

## Adding Additional Tech

Astro is flexible and supports many integrations. A few starting points:

- [Astro Integrations](https://docs.astro.build/en/guides/integrations-guide/) – official and community packages (Tailwind, MDX, image optimizers, adapters).
- [Content Collections](https://docs.astro.build/en/guides/content-collections/) – typed content authoring for blogs, docs, or marketing pages.
- [SSR & Adapters](https://docs.astro.build/en/guides/server-side-rendering/) – switch from static output to SSR if your deployment needs it.
- [React Ecosystem](https://docs.astro.build/en/guides/integrations-guide/react/) – guidance on using React libraries within Astro islands.

### Component Libraries

All new projects are expected to align with a design system. Work with your DS488 design team to determine the component library (e.g., Material UI, Chakra UI, Tailwind UI) that best matches the provided design kit, then integrate it within Astro/React islands.

## Backend (FastAPI) — Run & deploy

This repository includes a small FastAPI app at `app/main.py` that exposes a POST endpoint for creating `sessions` records in Supabase via the REST API. Use the steps below to run it locally.

Quick steps (PowerShell):

```powershell
# create + activate a venv
python -m venv .venv
.venv\Scripts\Activate.ps1

# install Python dependencies
pip install -r requirements.txt

# copy the env template and edit with your Supabase values
copy .env.example .env
# then edit .env and set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY

# run the server (auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Test the API (example JSON body):

```json
{
  "address": "123 Main St",
  "city": "Louisville",
  "zipcode": "40202",
  "units": 12
}
```

POST to `http://127.0.0.1:8000/api/assessments`. The service uses the Supabase service role key (server secret) so do not commit your `.env` file with real credentials.

Notes:

- Ensure the `sessions` table exists in your Supabase project. Example SQL:

```sql
create extension if not exists pgcrypto;

create table public.assessments (
  id uuid primary key default gen_random_uuid(),
  address text,
  city text,
  zipcode text,
  units integer,
  created_at timestamptz default now()
);
```

- The requirements are listed in `requirements.txt`. For deployments, pin versions appropriately and follow your hosting provider's docs (e.g., Render, Fly, Heroku, or a containerized approach).
