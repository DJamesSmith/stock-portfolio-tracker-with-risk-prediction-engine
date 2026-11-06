# Stock Portfolio Risk & Forecasting Platform

A Django REST Framework backend where investors track stock portfolios and every holding gets two machine-learning outputs: a **risk label** (Low / Medium / High, Random Forest) and a **next-trading-day direction** (Up / Down, Gradient Boosting). It also has a small Bootstrap web interface for login, dashboards and portfolio pages.

**Author:** Dion James Smith

This README describes what is implemented in this repository today. Planned work that is not built yet is listed at the end.

---

## Contents

- [Technology](#technology)
- [Apps](#apps)
- [Data model](#data-model)
- [Roles and permissions](#roles-and-permissions)
- [Authentication](#authentication)
- [API response format](#api-response-format)
- [API endpoints](#api-endpoints)
- [Web pages](#web-pages)
- [Background tasks](#background-tasks)
- [Caching](#caching)
- [Machine learning](#machine-learning)
- [Project structure](#project-structure)
- [Setup](#setup)
- [Running the services](#running-the-services)
- [Loading data and training models](#loading-data-and-training-models)
- [Postman collection](#postman-collection)
- [Verifying the project](#verifying-the-project)
- [Logging](#logging)
- [Not implemented yet](#not-implemented-yet)
- [Machine learning disclaimer](#machine-learning-disclaimer)

---

## Technology

| Area | Used |
|---|---|
| Framework | Django 6.1, Django REST Framework 3.18 (function-based views) |
| Database | PostgreSQL (psycopg 3) |
| Auth | Custom `User` model, JWT with **PyJWT** (not SimpleJWT) |
| Background jobs | Celery 5.6 with Redis broker and Celery Beat |
| Cache / throttling / token blacklist | Redis through Django's built-in `RedisCache` |
| Market data | Kaggle CSV backfill + `yfinance` for new daily prices |
| ML | pandas, NumPy, scikit-learn, joblib |
| Web UI | Django templates + Bootstrap |

## Apps

| App | Responsibility |
|---|---|
| `accounts` | Custom `User`, registration, login, JWT access/refresh, logout blacklist, profile, change password, admin role and analyst assignment, web login pages |
| `core` | Shared code used by every app: `ApplicationLogger`, `@log_execution_time`, `@admin_required`, `api_response`, permissions, pagination, exception handler, throttles, cache keys and invalidation, multiple-file upload field, Celery `ping` task |
| `market_data` | `PriceHistory` and `DatasetUpload` models, dataset upload pages (CSV files, folders, zip), `yfinance` provider, price ingestion tasks, price APIs |
| `portfolios` | `Portfolio` and `Holding`, CRUD APIs, role-scoped querysets, portfolio summary |
| `analytics` | Uses the trained models: prediction tasks, risk/forecast APIs, portfolio risk summary |
| `ml_training` | All machine-learning training: the three algorithms, features, labels, dataset split, model registry, `TrainingRun` model, training pages for admins |
| `dashboards` | Investor, analyst and admin dashboards (API and web), holding price trend, portfolio and holding web pages |

Validation uses Django **ModelForms / Forms**. DRF **serializers are used only for output**.

## Data model

```text
User (role, assigned_analyst -> User)
 └── Portfolio (user)
      └── Holding (portfolio, ticker, ML output fields)
                    ticker ··· matched by string ··· PriceHistory (ticker, date)
```

- **User** (`users` table): `username`, `email`, `role` (`investor` / `analyst` / `admin`), `assigned_analyst` (self foreign key, only investors keep one), `is_active`, `is_staff`, `date_joined`, `updated_at`. Saving a user with role `admin` sets `is_staff` and `is_superuser`; other roles clear them.
- **Portfolio** (`portfolios`): `user`, `name` (unique per user, case-insensitive check), `description`, timestamps.
- **Holding** (`holdings`): `ticker` (stored uppercase), `quantity` and `buy_price` (must be > 0), `buy_date` (not in the future), plus read-only ML fields: `risk_label` (`low`/`medium`/`high`), `risk_score`, `predicted_direction` (`up`/`down`), `prediction_confidence`, `last_predicted_at`, `risk_model_version`, `forecast_model_version`.
- **PriceHistory** (`price_history`): `ticker`, `date`, `open_price`, `high_price`, `low_price`, `close_price` (Decimal 12,4), `volume` (BigInteger, nullable), `created_at`. Unique on `(ticker, date)`.

There is no foreign key between `Holding` and `PriceHistory`: price rows are shared by every investor who holds that ticker.

## Roles and permissions

Data is scoped in the queryset, so a record the user may not see returns **404**, and a record they can see but not change returns **403**.

| Action | Investor | Analyst | Admin |
|---|---|---|---|
| Register / log in / own profile | Yes | Yes | Yes |
| View portfolios and holdings | Own only | Assigned investors only (read-only) | All |
| Create / edit / delete portfolios and holdings | Own only | No | Yes (can create a portfolio for an investor with `user_id`) |
| Latest price and price history | Yes | Yes | Yes |
| Queue a price refresh | No | Yes | Yes |
| View risk, forecast, risk summary, trend | Own only | Assigned investors | All |
| Queue ML recomputation / check task status | No | Yes (assigned investors' holdings) | Yes |
| Investor / analyst / admin dashboard | Investor dashboard | Analyst dashboard | Admin dashboard |
| List users, change role, assign analyst | No | No | Yes (cannot change own role) |

Role change rules: an admin cannot change their own role; demoting an analyst unassigns all of their investors (in one transaction); a user who stops being an investor loses their assigned analyst.

## Authentication

- `POST /api/accounts/login/` accepts `username_or_email` + `password` and returns an **access token (15 minutes)** and a **refresh token (7 days)**. Lifetimes come from `.env`.
- Send the access token as `Authorization: Bearer <access>`.
- Access and refresh tokens are signed with **different secrets** (`JWT_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY`) and carry a `token_type` claim, so one cannot be used as the other.
- Refresh tokens have a `jti`. Logout stores it in a separate Redis database (`TOKEN_BLACKLIST_REDIS_URL`) until the token would expire.
- Every token includes a short hash of the password. After a password change, all older access and refresh tokens stop working; the change-password response returns a new pair.
- Login: missing fields → 400, wrong credentials → 401, inactive account → 403.
- Throttles (Redis backed): login `5/minute` per IP, register `10/hour` per IP, price refresh `10/hour` per user. Over the limit → 429 with `retry_after_seconds`.

## API response format

Every API response, including errors, uses the same shape:

```json
{
    "status": "success",
    "message": "Portfolio retrieved.",
    "data": { },
    "errors": null
}
```

Validation errors put field messages in `errors`, for example `{"quantity": ["Ensure this value is greater than or equal to 0.0001."]}`. Lists are paginated inside `data` as `count`, `next`, `previous`, `results` (20 per page, `?page_size=` up to 100). Unexpected server errors return 500 in the same shape and are logged.

## API endpoints

### Accounts — `/api/accounts/`

| Method | Endpoint | Access | Notes |
|---|---|---|---|
| POST | `register/` | Public | Always creates an investor |
| POST | `login/` | Public | Returns user + tokens |
| POST | `token/refresh/` | Valid refresh token | Body `{"refresh": "..."}` |
| POST | `logout/` | Authenticated | Body `{"refresh": "..."}`; blacklists it |
| GET / PATCH | `me/` | Authenticated | PATCH changes `username` / `email` only |
| POST | `change-password/` | Authenticated | `old_password`, `new_password`, `new_password_confirmation` |
| GET | `users/` | Admin | Paginated |
| PATCH | `users/{id}/` | Admin | `role`, `assigned_analyst` |

### Portfolios and holdings — `/api/`

| Method | Endpoint | Access |
|---|---|---|
| GET / POST | `portfolios/` | GET everyone (scoped); POST investor or admin |
| GET / PATCH / DELETE | `portfolios/{id}/` | GET visible; PATCH/DELETE owner or admin |
| GET | `portfolios/{id}/summary/` | Visible |
| GET / POST | `portfolios/{id}/holdings/` | GET visible; POST owner or admin |
| GET / PATCH / DELETE | `holdings/{id}/` | GET visible; PATCH/DELETE owner or admin |

Adding a holding for a ticker with no price in the last 7 days queues `refresh_single_ticker`; the request itself never calls the market provider. `ticker` cannot be changed after creation, and ML fields are rejected on create and update.

The summary returns total cost, current value, unrealised gain/loss (amount and %), a risk distribution and one row per holding. Holdings without a stored price are valued at their buy price.

### Market data — `/api/market/`

| Method | Endpoint | Access | Notes |
|---|---|---|---|
| GET | `prices/{ticker}/` | Authenticated | Latest stored row, 404 if none |
| GET | `prices/{ticker}/history/` | Authenticated | `?start=YYYY-MM-DD&end=YYYY-MM-DD`, newest first, paginated |
| POST | `refresh/{ticker}/` | Analyst / Admin | 202 with `task_id`; 503 if the broker is down |

### Analytics — `/api/analytics/`

| Method | Endpoint | Access |
|---|---|---|
| GET | `holdings/{id}/risk/` | Visible holding |
| GET | `holdings/{id}/forecast/` | Visible holding |
| POST | `holdings/{id}/recompute/` | Analyst / Admin (202 with `task_id`) |
| GET | `portfolio/{id}/risk-summary/` | Visible portfolio |
| GET | `tasks/{task_id}/` | Analyst / Admin — Celery state and result |

The risk summary returns `risk_distribution`, `direction_distribution`, `average_confidence` (mean `risk_score`), `average_forecast_confidence` and `total_value`.

### Dashboards — `/api/dashboard/`

| Method | Endpoint | Access |
|---|---|---|
| GET | `investor/` | Investor |
| GET | `analyst/` | Analyst |
| GET | `admin/` | Admin |
| GET | `holdings/{id}/trend/` | Visible holding (`?start=&end=`, default last 180 days) |

Summary, risk-summary and dashboard responses include `from_cache` so you can see whether Redis served them.

## Web pages

Session-based pages built with Django templates (separate from the JWT API):

| URL | Page |
|---|---|
| `/` | Home |
| `/register/`, `/login/`, `/logout/` (POST) | Account pages |
| `/dashboard/` | Role-specific dashboard |
| `/profile/`, `/profile/password/` | Profile and change password |
| `/users/`, `/users/{id}/update/` | Admin user management |
| `/portfolios/`, `/portfolios/{id}/` | Portfolio list and detail |
| `/holdings/{id}/` | Holding detail with price chart |
| `/datasets/` | Admin: upload price CSV files, a folder or a zip; upload history; fetch latest prices |
| `/datasets/{id}/` | Admin: progress and per-file results of one upload |
| `/ml/` | Admin: start training, data readiness, models in use, training history |
| `/ml/runs/{id}/` | Admin: progress and results of one training run (cancel while waiting) |
| `/ml/models/` | Admin: every saved model version (`?type=risk` or `?type=forecast`) |
| `/ml/models/{type}/{version}/` | Admin: metrics, baseline comparison, confusion matrix, feature importance, parameters |
| `/admin/` | Django admin |

Investors and analysts who open an admin page are sent back to their dashboard with a message.

## Background tasks

| Task | Trigger | What it does |
|---|---|---|
| `core.tasks.ping` | Beat, every 15 minutes | Health check, returns `pong` |
| `market_data.tasks.fetch_daily_prices` | Beat, Mon–Fri 22:00 UTC | For every stored ticker plus `MARKET_SEED_TICKERS`, fetches dates after the latest stored date and saves them |
| `market_data.tasks.refresh_single_ticker` | Refresh API, new holding | Same for one ticker; retries 3 times with 60s / 120s / 240s back-off |
| `analytics.tasks.recompute_holding_risk` | Beat, Mon–Fri 23:00 UTC | Risk prediction for all holdings |
| `analytics.tasks.recompute_holding_forecast` | Beat, Mon–Fri 23:15 UTC | Direction prediction for all holdings |
| `analytics.tasks.recompute_single_holding` | Recompute API | Both predictions for one holding |
| `market_data.tasks.import_dataset_upload` | Datasets page upload | Loads the uploaded CSV files into `PriceHistory`, updating progress after every file |
| `ml_training.tasks.run_training` | ML Training page | Trains the chosen models and optionally updates every holding's prediction |
| `ml_training.tasks.retrain_models` | Beat, Sunday 02:00 UTC | Creates a `TrainingRun` and trains both models (skipped if a run is already active) |

Holdings whose ticker has too little history are skipped and reported in the task result. Failed tasks are logged with task name and arguments.

Redis databases:

| DB | Use |
|---|---|
| 0 | Celery broker |
| 1 | Celery results |
| 2 | Django cache and throttle counters |
| 3 | Refresh-token blacklist |

Settings refuse to start if these four URLs are not different, so clearing the cache can never remove queued tasks or blacklisted tokens.

## Caching

| Data | TTL | Cleared when |
|---|---|---|
| Portfolio summary, portfolio risk summary | `CACHE_TTL_SECONDS` (300) | Portfolio or holding changes, new prices for a held ticker, new predictions |
| Investor, analyst, admin dashboards | 300 seconds | The same events, plus registrations and role/assignment changes |

## Machine learning

**Features** (per ticker, calculated only from past rows, so adding later prices never changes earlier features):
`daily_return`, `volatility_30`, `volatility_90`, `max_drawdown_90`, `price_to_ma_20`, `price_to_ma_50`, `rsi_14`, `volume_trend` (20-day / 90-day average volume; 1.0 when volume is missing).

**Risk model** — `RandomForestClassifier`
- Label: standard deviation of daily returns over the **next 30 trading days**, cut into low / medium / high using the training set's 33rd and 66th percentiles.
- Compared with a `LogisticRegression` baseline (macro F1).
- `risk_score` is the probability of the predicted class.

**Direction model** — `HistGradientBoostingClassifier`
- Label: `up` if the next trading day's close is above today's close, otherwise `down`.
- Compared with "always up" and "same as today" baselines.
- `prediction_confidence` is the probability of the predicted class.

**Time-based split:** train up to 2022-12-31, validation 2023, test 2024 onwards. The risk split leaves a 45-day gap so 30-day-ahead labels do not overlap the next split.

**Where the code is:** everything for training is in `ml_training/`:

| File | Contains |
|---|---|
| `algorithms.py` | `RandomForestClassifier`, `LogisticRegression` and `HistGradientBoostingClassifier` with their settings |
| `feature_engineering.py` | The eight features |
| `labels.py` | Risk and direction labels |
| `dataset.py` | Loading prices and the date split |
| `train_risk.py` | Trains and evaluates the risk model against the baseline |
| `train_forecast.py` | Trains and evaluates the forecast model against the baselines |
| `registry.py` | Saving, versioning and loading models |
| `services.py` | Runs a `TrainingRun` and builds the data shown on the training pages |

`analytics/services/predict.py` loads the newest saved models and writes predictions to holdings.

**Model registry:** models are saved to `ml_models/<risk|forecast>/<version>.joblib` with a `<version>.json` metadata file (features, training window, label thresholds, parameters, metrics, baseline comparison). Versions look like `risk-rf-2026.11.03-01`. Prediction always uses the newest version and stores it on the holding (`risk_model_version`, `forecast_model_version`).

## Project structure

```text
stock_risk_engine/
├── accounts/            models, managers, forms, serializers, utils (JWT), authentication,
│                        permissions, urls/{api_urls,urls}.py, views/{api_views,views}.py
├── analytics/           serializers.py, tasks.py, services/{predict,risk_summary}.py, views.py, urls.py
├── core/                application_logger.py, decorators.py, responses.py, fields.py, cache.py,
│                        exceptions.py, pagination.py, permissions.py, tasks.py, throttles.py
├── dashboards/          selectors.py, services.py, serializers.py, templatetags/,
│                        urls/{api_urls,urls}.py, views/{api_views,views}.py
├── market_data/         models, forms, selectors, serializers, tasks, urls/{api_urls,urls}.py,
│                        views/{api_views,views}.py, services/{provider,ingestion,dataset_upload}.py
├── ml_training/         algorithms.py, feature_engineering.py, labels.py, dataset.py, train_risk.py,
│                        train_forecast.py, registry.py, models.py, forms.py, services.py, tasks.py,
│                        views.py, urls.py, templatetags/ml_tags.py
├── portfolios/          models, forms, selectors, services, serializers, cache.py, views, urls
├── stock_risk_engine/   settings.py, urls.py, celery.py, wsgi.py, asgi.py
├── templates/           base.html, accounts/, core/, dashboards/, market_data/, ml_training/
├── script/js/           script.js, price_chart.js
├── ml_models/           trained models (git-ignored)
├── media/               uploaded files while they are imported (git-ignored)
├── logs/                app.log (git-ignored)
├── .env.example
├── requirements.txt
└── stock_risk_engine.postman_collection.json
```

## Setup

Requirements: Python 3.12+, PostgreSQL, Redis.

Uploaded files are stored in `media/` (`MEDIA_ROOT`) until they are imported. `DATA_UPLOAD_MAX_NUMBER_FILES` is set to 1000 so a full folder of S&P 500 CSV files can be uploaded at once.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`. Generate the three secrets separately (they must all be different):

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Create the database:

```sql
CREATE USER django_user WITH PASSWORD 'your-password';
CREATE DATABASE stock_risk_prediction_db OWNER django_user;
```

Then:

```bash
python manage.py migrate
python manage.py createsuperuser
```

`createsuperuser` always creates a user with the `admin` role.

## Running the services

Use separate terminals from the project folder:

```bash
redis-server
python manage.py runserver
celery -A stock_risk_engine worker -l info
celery -A stock_risk_engine beat -l info
```

Check the worker:

```bash
python manage.py shell -c "from core.tasks import ping; print(ping.delay().get(timeout=10))"
```

It prints `pong`.

## Loading data and training models

Everything is done from the web pages while logged in as an admin. The Celery worker must be running, because uploads and training run in the background.

**1. Upload the dataset** — open **Datasets** in the top bar.

Historical prices come from the Kaggle dataset *S&P 500 Stocks, Daily Historical Data (10 Years)*: one CSV per ticker (for example `AAPL.csv`) with Date, Open, High, Low, Close and Volume columns. You can upload it in any of these ways:

- pick several CSV files,
- pick the whole folder (other files in it, such as `.DS_Store`, are ignored),
- pick the Kaggle `.zip` exactly as it downloads (folders and `__MACOSX` entries inside it are handled).

Optionally list tickers to load only those. The upload page shows a progress bar (files done / total) and refreshes itself. When it finishes, the upload page lists every file with rows added and skipped, and any file that had a problem (bad file name, missing columns, unreadable file). Rows that are already stored are skipped, so uploading the same files again is safe. Uploaded files are deleted after the import.

**Fetch now** on the same page downloads any missing recent prices from Yahoo Finance for every tracked ticker (the same job runs every weekday at 22:00 UTC).

**2. Train the models** — open **ML Training**.

- The *Training data* card shows whether the stored prices cover all three periods (2022 or earlier, 2023, 2024 onwards). **Start training** stays disabled until they do.
- Choose both models, the risk model only, or the forecast model only, optionally limit the tickers, and choose whether to update every holding's prediction when training finishes.
- The run page shows the current step and refreshes itself. When it finishes it shows the test results for each model next to its baselines and links to the new versions. Errors (for example a missing period) are shown on the page.
- Only one run can be active at a time. A run that is still waiting for a worker can be cancelled.
- **Model versions** lists every saved model; open one to see its date split, label thresholds, baseline comparison, per-class scores, confusion matrix, feature importance and parameters.

Predictions are also written by the scheduled tasks, or straight away for one holding with `POST /api/analytics/holdings/{id}/recompute/`.

## Postman collection

`stock_risk_engine.postman_collection.json` runs the main workflow from top to bottom:

0. Setup — register an investor and a second user, log in as admin and investor
1. Admin — list users, promote the second user to analyst, assign them to the investor, admin dashboard, log in as analyst
2. Investor — profile, portfolio and holding CRUD, summary, prices, dashboard, trend
3. Analyst — read-only access checks, queue a price refresh and a recompute, task status, analyst dashboard
4. Analytics — risk, forecast and risk summary for the holding
5. Change password, cleanup and logout — then check the old refresh token is rejected

Before running, set the collection variables `admin_username` and `admin_password` to your superuser, and make sure the default `ticker` (`AAPL`) has price data. Each run creates new users with a unique suffix.

**Automatic token refresh:** each role folder's pre-request script keeps separate tokens for admin, investor and analyst. If the active role's access token expires within 60 seconds, it calls `/api/accounts/token/refresh/` first and continues with the new token.

Every request checks its status code and the `status`/`message`/`data`/`errors` shape. Run it in Postman (Run collection) or with Newman:

```bash
newman run stock_risk_engine.postman_collection.json --env-var admin_password='your-admin-password'
```

Registration is limited to 10 per hour per IP and each run registers 3 users, so you can run the collection about 3 times an hour.

## Verifying the project

The repository does not include an automated test suite. To check a working setup:

1. `python manage.py check` reports no issues and `python manage.py makemigrations --check` reports no changes.
2. The Celery `ping` check above prints `pong`.
3. The Postman collection passes end to end with the worker running.

## Logging

`ApplicationLogger` writes to `logs/app.log` (rotating, 5 MB × 5 files) with UTC timestamps. It records logins, permission denials, cache hits and clears, task results, failures and timings from `@log_execution_time`.

## Not implemented yet

- Docker / docker-compose and production settings (the project runs locally with `DEBUG = True`)
- OpenAPI / Swagger documentation
- Flutter client, push notifications, WebSockets
- Sector analytics, rebalancing suggestions, LSTM forecasting

## Machine learning disclaimer

Risk labels and direction forecasts are statistical estimates from historical prices. Next-day direction accuracy around 50–55% is normal and does not make a useful trading strategy. Nothing here is financial advice.
