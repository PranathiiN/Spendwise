# SpendWise

SpendWise is a personal finance web app. You can record income and expenses, organise them into categories, set monthly budgets with warnings, track savings goals, and view a dashboard and monthly reports. Each user can only see their own data.

> **Phase 2:** AI category suggestions, monthly insights, a chat assistant and receipt scanning use the Claude API and switch on when `ANTHROPIC_API_KEY` is set. Month-end forecasting is plain arithmetic and always on. Bank integrations are still planned. See [AI features](#ai-features-phase-2).

| Layer    | Stack |
|----------|-------|
| Backend  | Python 3.12+, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, PostgreSQL (psycopg 3), PyJWT, pwdlib (Argon2), pytest + httpx |
| Frontend | React 19, TypeScript, Vite, React Router, Axios, Recharts, Tailwind CSS v4, React Hook Form, Zod |
| Database | PostgreSQL via `DATABASE_URL`, local or [Neon](https://neon.tech) |

---

## Project structure

```
C:\Spendwise
├── backend/
│   ├── app/
│   │   ├── api/routes/      auth, categories, transactions, budgets, goals, dashboard, reports
│   │   ├── api/utils.py     shared route helpers
│   │   ├── core/            config (env settings), security (JWT, Argon2), dependencies
│   │   ├── db/              declarative base, engine/session, system-category seed
│   │   ├── models/          user, category, transaction, budget, savings_goal (+ enums, mixins)
│   │   ├── schemas/         Pydantic request/response models
│   │   ├── services/        dashboard, budget, report, goal and category logic
│   │   ├── utils/           date and Decimal money helpers
│   │   └── main.py          FastAPI app, CORS, router registration, /api/health
│   ├── alembic/             migrations (0001 creates all tables and default categories)
│   ├── tests/               pytest suite (runs against a real PostgreSQL test database)
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/             axios client and one module per resource
│   │   ├── components/      layout, common, dashboard, transactions, budgets, goals, categories
│   │   ├── contexts/        AuthContext
│   │   ├── hooks/           useApi, useCategories, useCurrency, useDebounce
│   │   ├── pages/           Login, Register, Dashboard, Transactions, Budgets, SavingsGoals, Reports, Settings
│   │   ├── routes/          ProtectedRoute and PublicOnlyRoute
│   │   ├── types/           shared TypeScript types
│   │   └── utils/           currency, dates, colors
│   ├── package.json
│   └── .env.example
├── .gitignore
└── README.md
```

**Differences from the suggested structure:**
- `C:\Spendwise` is the project root, so there is no extra `spendwise/` folder inside it.
- Added `services/category_service.py` and `services/goal_service.py`. Ownership checks and goal progress maths are used by several routes, so they live in one place.
- Added `app/utils/` with Decimal money and month helpers.
- Added `frontend/src/api/categories.ts` and `components/categories/`, which the settings page needs.
- Added `tests/test_categories.py`.

---

## Prerequisites (Windows)

- **Python 3.12+**: `py --version`
- **Node.js 20+** (LTS): `node --version`
- **PostgreSQL 15+**, either installed locally or a free Neon project
- **Git**

---

## 1. Create the databases

You need **two** databases. The app uses one, and the other is used only by tests, which drop and recreate every table in it.

**Local PostgreSQL** (PowerShell):

```powershell
psql -U postgres -c "CREATE DATABASE spendwise;"
psql -U postgres -c "CREATE DATABASE spendwise_test;"
```

**Neon:** create a project, then create a second database (or branch) for tests. Copy each connection string. They look like this:

```
postgresql://USER:PASSWORD@ep-xxxx-xxxx.ap-southeast-1.aws.neon.tech/spendwise?sslmode=require
```

You can paste the URL exactly as Neon gives it. The backend switches it to the psycopg 3 driver automatically and keeps `sslmode` and `channel_binding`.

---

## 2. Backend setup

```powershell
cd C:\Spendwise\backend

py -3.12 -m venv .venv
# If activation is blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt

Copy-Item .env.example .env
# Generate a JWT secret and paste it into .env as JWT_SECRET_KEY:
python -c "import secrets; print(secrets.token_urlsafe(48))"
notepad .env      # set DATABASE_URL, TEST_DATABASE_URL, JWT_SECRET_KEY
                  # optional: ANTHROPIC_API_KEY to turn on AI features
```

Create the tables and default categories, then start the API:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs. Use **Authorize** and paste the `access_token` from `/api/auth/login`.
- Health check: http://localhost:8000/api/health

### Run the backend tests

```powershell
cd C:\Spendwise\backend
.\.venv\Scripts\Activate.ps1
pytest -v
```

The tests read `TEST_DATABASE_URL` from `.env`. They refuse to run if it is missing or equal to `DATABASE_URL`.

The AI tests use a fake Claude client. The test suite never calls the real Claude API, even when `ANTHROPIC_API_KEY` is set.

---

## 3. Frontend setup

Open a second PowerShell window:

```powershell
cd C:\Spendwise\frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open http://localhost:5173, register an account and start adding transactions.

Other commands:

```powershell
npm run typecheck   # TypeScript check only
npm run build       # type-check and production build into dist/
npm run preview     # serve the production build
```

---

## 4. Git

```powershell
cd C:\Spendwise
git init
git add .
git status          # confirm that no .env file is listed
git commit -m "SpendWise phase 1: full-stack personal finance app"
```

`.gitignore` excludes `.env`, `.env.*` (but keeps `.env.example`), virtual environments, `node_modules` and build output.

---

## Features

| Area | What you get |
|------|--------------|
| Auth | Register, log in, profile (name and currency), change password. Argon2id hashing, JWT bearer tokens, email lower-cased and unique. Login gives the same error and similar timing for unknown emails and wrong passwords. |
| Categories | 19 shared default categories (12 expense, 7 income). Users can add private custom categories, which they can rename, recolour and delete (only while no transactions use them). |
| Transactions | Create, edit and delete. Search description and notes; filter by type, category, payment method, date range and amount range; sort; paginate. Shows income and expense totals for the filtered results. |
| Budgets | One limit per expense category per month, with a configurable alert threshold (default 80%). Live spent, remaining and % used, with an **OK / Near limit / Over budget** status. Can copy last month's budgets. |
| Savings goals | Target amount and date, deposit or withdraw, progress %, monthly amount needed to stay on track, and **active / completed / overdue** status. |
| Dashboard | Month totals with change vs last month, savings rate, 6-month income vs expense chart, spending-by-category donut, recent transactions, budget alerts and goal progress. |
| Reports | Monthly report: daily spending, expense and income by category, top expenses, budget performance, 6-month trend, and CSV export (Excel-friendly, protected against formula injection). |

### API overview (all under `/api`)

```
POST   /auth/register            POST /auth/login           GET/PATCH /auth/me
POST   /auth/change-password
GET    /categories               POST /categories           PATCH/DELETE /categories/{id}
GET    /transactions             POST /transactions         GET/PATCH/DELETE /transactions/{id}
GET    /budgets?month=YYYY-MM    POST /budgets              GET/PATCH/DELETE /budgets/{id}
POST   /budgets/copy-previous?month=YYYY-MM
GET    /goals                    POST /goals                GET/PATCH/DELETE /goals/{id}
POST   /goals/{id}/contribute
GET    /dashboard?month=YYYY-MM
GET    /reports/monthly?month=YYYY-MM
GET    /reports/monthly/export?month=YYYY-MM   (CSV)
GET    /forecast?month=YYYY-MM   (current month only)
GET    /ai/status                POST /ai/categorize        GET /ai/insights?month=YYYY-MM
POST   /ai/chat                  POST /ai/receipt           (multipart file upload)
GET    /health
```

---

## AI features (phase 2)

| Feature | Where | How it works |
|---------|-------|--------------|
| Category suggestions (SW-12) | Add-transaction form | After you type a description, a suggested category appears with a **Use** button. It first reuses the category you last chose for the same description, so it learns from your corrections without calling the AI. Otherwise Claude picks from your own categories of the right type. Nothing is saved until you submit. |
| Insights (SW-13) | Dashboard and Reports | **Generate insights** writes 3-5 short observations. The backend computes every figure with the same code as the dashboard; Claude only writes the wording and must cite the figures it used, which are shown under **Based on**. Needs at least 5 transactions in the month. Results are cached until your data changes. |
| Assistant (SW-14) | **Assistant** page | Ask questions such as "How much did I spend on food last month?". Claude answers using read-only tools that call the existing services for your own data only. Each answer lists the data it used. It can't add, edit or delete anything. |
| Forecast (SW-15) | Dashboard | Projected month-end spending, budgets likely to go over, and when each savings goal will be reached at its current pace. Plain arithmetic, no AI, labelled as an estimate. Needs at least 2 months of transactions and only covers the current month. |
| Receipt scanning (SW-16) | Add-transaction form | Upload a JPEG, PNG, WebP, GIF or PDF (max 5 MB). Claude reads the merchant, date and total and fills in the form for you to check. Amounts are validated as 2-decimal strings. The receipt file isn't stored. |

**Turning AI on:** get an API key at [console.anthropic.com](https://console.anthropic.com), add `ANTHROPIC_API_KEY=...` to `backend\.env`, and restart the backend. `AI_MODEL` defaults to `claude-opus-5-5`. Without a key, AI features show a "switched off" message, history-based category suggestions and forecasts still work, and the rest of the app is unaffected. Each AI action is a paid API call. Insights only run when you click the button, and they're cached.

---

## Design decisions

- **Money is never a float.** Columns are `NUMERIC(12,2)` and Python uses `Decimal`. Values travel in JSON as strings (`"1234.50"`). The frontend only converts them to numbers to display them or draw charts, and sends the user's typed string back unchanged.
- **Data isolation.** Every query filters on the logged-in user's id. Requests for another user's records return `404` (not `403`), so their existence isn't revealed. Using another user's custom category returns the same error as a missing category.
- **Validation in layers.** Pydantic enforces positive amounts with at most 2 decimals, valid enums and lengths. Routes enforce business rules (category type must match the transaction type, budgets only on expense categories). PostgreSQL `CHECK` and `UNIQUE` constraints back up both.
- **Budget status:** *Over budget* when spent > limit; *Near limit* when % used ≥ threshold (this includes exactly reaching the limit); otherwise *On track*.
- **Tokens:** a single access token (60 min by default) is stored in `localStorage`. This is simple and fits phase 1. For production, consider short-lived access tokens plus an httpOnly refresh cookie, and add login rate limiting.
- **No Docker.** Setup is plain Python and Node, as requested.

## Ideas for the next phase

Bank integrations (SW-17), recurring transactions, goal contribution history (would make goal forecasts more accurate), refresh tokens and rate limiting, and a dark theme.
