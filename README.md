# Stock Portfolio Risk & Forecasting Platform

> A Django REST Framework backend combining JWT-secured, role-based
> portfolio management with a machine-learning risk and forecast engine,
> designed API-first for future Flutter integration.

**Author:** Dion James Smith\
**Version:** 1.0\
**Documentation:** September 2026


## Table of Contents

-   [Overview](#overview)
-   [Project Objectives](#project-objectives)
-   [Core Capabilities](#core-capabilities)
-   [Technology Stack](#technology-stack)
-   [System Architecture](#system-architecture)
-   [Django Application Structure](#django-application-structure)
-   [Database Design](#database-design)
-   [Authentication and
    Authorization](#authentication-and-authorization)
-   [Roles and Permissions](#roles-and-permissions)
-   [REST API](#rest-api)
-   [Serializers](#serializers)
-   [Celery and Redis](#celery-and-redis)
-   [Machine Learning Pipeline](#machine-learning-pipeline)
-   [Dataset](#dataset)
-   [Environment Configuration](#environment-configuration)
-   [Project Directory Structure](#project-directory-structure)
-   [Installation and Local
    Development](#installation-and-local-development)
-   [Running Django](#running-django)
-   [Running Celery and Redis](#running-celery-and-redis)
-   [Database Setup](#database-setup)
-   [Authentication Flow](#authentication-flow)
-   [End-to-End Workflow](#end-to-end-workflow)
-   [Security Considerations](#security-considerations)
-   [Performance and Non-Functional
    Considerations](#performance-and-non-functional-considerations)
-   [Flutter Integration Readiness](#flutter-integration-readiness)
-   [Future Scope](#future-scope)
-   [Machine Learning Disclaimer](#machine-learning-disclaimer)
-   [Development Roadmap](#development-roadmap)
-   [License](#license)


## Overview

The **Stock Portfolio Risk & Forecasting Platform** is an API-first
backend application built with **Django** and **Django REST Framework
(DRF)**.

The platform is designed to allow investors to:

-   Create and manage investment portfolios.
-   Add and manage individual stock holdings.
-   Retrieve historical and current market data.
-   View portfolio value and holding-level information.
-   Receive machine-learning-driven risk classifications.
-   Receive short-term stock price direction forecasts.
-   View prediction confidence and portfolio-level risk summaries.

The backend is deliberately client-agnostic. Its functionality is
exposed through versioned REST APIs so that the same backend can support
a web dashboard, Postman-based API testing, or a future **Flutter mobile
application** without requiring changes to the core backend
architecture.

The platform combines:

-   Django
-   Django REST Framework
-   PostgreSQL
-   Custom user authentication
-   JWT access and refresh tokens
-   Role-based and object-level authorization
-   Celery
-   Redis
-   Scikit-learn
-   Technical-indicator feature engineering
-   Asynchronous market-data ingestion
-   Scheduled machine-learning inference
-   Periodic model retraining
-   Redis-backed API response caching


## Project Objectives

This project is intended to demonstrate practical backend engineering,
database, asynchronous processing, API design, and applied
machine-learning capabilities within a single coherent system.

### 1. Custom Authentication Architecture

The platform uses a dedicated `accounts` application with a custom
`User` model.

Authentication is designed around:

-   Custom user management.
-   JWT access tokens.
-   JWT refresh tokens.
-   Separate JWT signing secrets.
-   Token refresh.
-   Refresh-token invalidation/blacklisting.
-   Role-based authorization.
-   Object-level authorization.
-   Analyst-to-investor assignment.

The architecture intentionally avoids simply relying on Django's default
user model.

### 2. Relational Database Design

The database is designed around normalized relational entities:

``` text
User
  |
  └── Portfolio
        |
        └── Holding
              |
              └── ticker → PriceHistory
```

The `User` model also contains a self-referencing relationship used to
represent analyst-to-investor assignment.

The system uses Django ORM joins and aggregations rather than raw SQL.

### 3. Applied and Explainable Machine Learning

Two supervised classification models form the analytics layer:

1.  **Random Forest Classifier**
    -   Predicts holding risk level.
    -   Produces Low / Medium / High risk classification.
    -   Provides a probability-based risk score.
    -   Supports feature-importance analysis.
2.  **Gradient Boosting Classifier**
    -   Predicts next-trading-day price direction.
    -   Produces Up / Down classification.
    -   Provides prediction confidence.

A Logistic Regression baseline is also planned for comparison against
the Random Forest model.

### 4. Asynchronous System Design

Celery and Redis are used for work that should not block normal HTTP
requests.

Background processing includes:

-   Daily market-data ingestion.
-   Individual ticker refresh.
-   Nightly risk recomputation.
-   Nightly forecast recomputation.
-   Periodic model retraining.
-   Cache invalidation.

### 5. API-First Architecture

Every major capability is exposed through REST endpoints and DRF
serializers.

This keeps the backend independent of the client implementation and
makes it suitable for:

-   Postman
-   Web applications
-   Flutter
-   Other mobile applications
-   Future third-party clients


## Core Capabilities

### Portfolio Management

Investors can:

-   Create portfolios.
-   Update portfolio information.
-   Delete portfolios.
-   View portfolio details.
-   Add stock holdings.
-   Update holdings.
-   Remove holdings.
-   View portfolio summaries.

### Market Data

The platform stores daily OHLCV market data:

-   Open
-   High
-   Low
-   Close
-   Volume

Historical market data is associated with a ticker rather than a
particular user or holding.

This allows the same market data to be shared by every portfolio that
contains the same stock.

### Risk Prediction

For each holding, the analytics layer produces:

-   `risk_label`
-   `risk_score`
-   `last_predicted_at`

Risk levels are:

``` text
Low
Medium
High
```

### Directional Forecasting

The forecasting layer produces:

-   `predicted_direction`
-   `prediction_confidence`

Possible directional predictions are:

``` text
Up
Down
```

The project intentionally predicts **direction rather than an exact
future price**.

This makes the problem a binary classification task and provides a more
defensible ML objective than attempting to predict an exact future stock
price.

### Portfolio Risk Summary

The platform can aggregate holding-level predictions into
portfolio-level information including:

-   Total portfolio value.
-   Number of holdings.
-   Low-risk holding count.
-   Medium-risk holding count.
-   High-risk holding count.
-   Average prediction confidence.


# Technology Stack

  -----------------------------------------------------------------------
  Layer                   Technology              Purpose
  ----------------------- ----------------------- -----------------------
  Backend                 Django                  Application framework

  API                     Django REST Framework   REST API development

  Database                PostgreSQL              System of record

  ORM                     Django ORM              Database access

  Authentication          Custom JWT              Access and refresh
                                                  tokens

  Task Queue              Celery                  Background processing

  Broker                  Redis                   Celery message broker

  Task Results            Redis                   Celery result backend

  Cache                   Redis                   API response caching

  Machine Learning        Scikit-learn            Risk classification and
                                                  forecasting

  Models                  Random Forest           Risk classification

  Models                  Gradient Boosting       Directional forecasting

  Planned Client          Flutter                 Future mobile client

  API Testing             Postman / DRF Browsable Development and testing
                          API                     
  -----------------------------------------------------------------------


# System Architecture

The platform is organized into five logical layers.

``` text
┌─────────────────────────────────────────────┐
│                 Client Layer                │
│       Postman / Web / Future Flutter       │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│                  API Layer                  │
│ Django REST Framework + JWT + Permissions  │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│             Business Logic Layer            │
│       Serializers + ViewSets + Rules        │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│                  Data Layer                 │
│       Django ORM → PostgreSQL              │
└──────────────────────┬──────────────────────┘
                       │
                       │
                       ▼
┌─────────────────────────────────────────────┐
│             Asynchronous Layer              │
│      Celery Workers + Celery Beat + Redis  │
└─────────────────────────────────────────────┘
```


## Synchronous Request Flow

A typical authenticated API request follows this path:

``` text
Client
  ↓
JWT Authentication
  ↓
Permission Classes
  ↓
ViewSet
  ↓
Serializer
  ↓
Django ORM
  ↓
PostgreSQL
  ↓
Serializer
  ↓
Client
```

For expensive read-heavy aggregation endpoints:

``` text
Client
  ↓
API
  ↓
Redis Cache
  ├── Cache Hit → Response
  │
  └── Cache Miss
        ↓
      PostgreSQL
        ↓
      Compute Result
        ↓
      Store in Redis
        ↓
      Response
```


## Asynchronous Flow

Background operations are handled separately from the HTTP
request/response cycle.

``` text
Celery Beat
    ↓
Scheduled Task
    ↓
Redis Broker
    ↓
Celery Worker
    ↓
Business / ML Processing
    ↓
PostgreSQL
    ↓
Redis Cache Invalidation
```

Scheduled operations include:

-   Daily price ingestion.
-   Nightly risk recomputation.
-   Nightly directional forecasting.
-   Weekly/monthly model retraining.


# Django Application Structure

The project is divided into focused Django applications.

## `accounts`

Responsible for identity and authentication.

Responsibilities:

-   Custom `User` model.
-   Registration.
-   Login.
-   JWT access-token issuing.
-   JWT refresh.
-   Logout / refresh-token invalidation.
-   Profile management.
-   User management.
-   Role management.
-   Analyst assignment.

No other application defines a user-like model.


## `portfolios`

Responsible for portfolio and holding management.

Contains:

-   `Portfolio`
-   `Holding`

Responsibilities:

-   Portfolio CRUD.
-   Holding CRUD.
-   Portfolio summaries.
-   Holding-level information.
-   Portfolio ownership rules.

The ML output fields on `Holding` are read-only to clients.


## `market_data`

Responsible for historical and current market data.

Contains:

-   `PriceHistory`

Responsibilities:

-   Daily OHLCV data.
-   Historical price endpoints.
-   Latest-price retrieval.
-   Celery-based market-data ingestion.
-   Individual ticker refresh.


## `analytics`

Responsible for machine learning and analytics.

Responsibilities:

-   Feature engineering.
-   Risk model training.
-   Forecast model training.
-   Model evaluation.
-   Model retraining.
-   Risk inference.
-   Directional forecasting.
-   Celery analytics tasks.
-   Portfolio risk summaries.

The analytics application intentionally does not own a database table of
its own. It computes and annotates data owned by the `portfolios`
application.


## `core`

Contains shared cross-cutting functionality.

Responsibilities:

-   Custom permission classes.
-   Pagination.
-   Exception handling.
-   Redis-backed throttling.
-   Shared backend utilities.


# Database Design

The system uses four core database entities.

  Table            Django App    Purpose
  ---------------- ------------- ----------------------------
  `User`           accounts      System users
  `Portfolio`      portfolios    Investor portfolios
  `Holding`        portfolios    Individual stock positions
  `PriceHistory`   market_data   Historical OHLCV data


## User

  Field                   Type       Description
  ----------------------- ---------- ----------------------------
  `id`                    Integer    Primary key
  `username`              String     Unique username
  `email`                 String     Unique email
  `password`              String     Hashed password
  `role`                  Enum       investor / analyst / admin
  `assigned_analyst_id`   Integer    Self-referencing FK
  `is_active`             Boolean    Account status
  `date_joined`           DateTime   Creation timestamp
  `updated_at`            DateTime   Last update timestamp

### Analyst Assignment

The `assigned_analyst_id` field references the `User` table itself.

``` text
Analyst User
     ↑
     │ assigned_analyst_id
     │
Investor User
```

This allows the system to retrieve all investors assigned to a
particular analyst without introducing a separate assignment table.


## Portfolio

  Field           Type       Description
  --------------- ---------- -----------------------
  `id`            Integer    Primary key
  `user_id`       FK         Owning investor
  `name`          String     Portfolio name
  `description`   String     Optional description
  `created_at`    DateTime   Creation timestamp
  `updated_at`    DateTime   Last update timestamp

Relationship:

``` text
User 1 ──────── N Portfolio
```


## Holding

  Field                     Type       Description
  ------------------------- ---------- ----------------------------
  `id`                      Integer    Primary key
  `portfolio_id`            FK         Parent portfolio
  `ticker`                  String     Stock symbol
  `quantity`                Decimal    Number of shares
  `buy_price`               Decimal    Purchase price
  `buy_date`                Date       Purchase date
  `risk_label`              Enum       Low / Medium / High
  `risk_score`              Float      Risk probability
  `predicted_direction`     Enum       Up / Down
  `prediction_confidence`   Float      Prediction probability
  `last_predicted_at`       DateTime   Latest ML computation time

Relationship:

``` text
Portfolio 1 ──────── N Holding
```

The ML fields are read-only through the API. They are populated by the
analytics background tasks.


## PriceHistory

  Field           Type      Description
  --------------- --------- ----------------
  `id`            Integer   Primary key
  `ticker`        String    Stock symbol
  `date`          Date      Trading date
  `open_price`    Decimal   Opening price
  `close_price`   Decimal   Closing price
  `high_price`    Decimal   Highest price
  `low_price`     Decimal   Lowest price
  `volume`        Integer   Trading volume

`PriceHistory` is intentionally **not** connected to `Holding` through a
foreign key.

Instead:

``` text
Holding.ticker
      │
      │ matching ticker
      ▼
PriceHistory.ticker
```

This is a normalization decision because historical market data is
shared across every investor holding the same stock.

For example, if 1,000 users hold AAPL, the application should not store
1,000 copies of the same historical AAPL data.


# Authentication and Authorization

The platform uses custom JWT authentication.

## Registration

New users register through:

``` http
POST /api/accounts/register/
```

New accounts default to:

``` text
role = investor
```

Only administrators can subsequently modify roles.


## Login

``` http
POST /api/accounts/login/
```

Successful authentication produces:

-   Access token.
-   Refresh token.


## Access Token

Access tokens are short-lived:

``` text
15 minutes
```

They are sent using the standard Bearer authentication scheme:

``` http
Authorization: Bearer <access_token>
```


## Refresh Token

Refresh tokens remain valid for:

``` text
7 days
```

When an access token expires, the client can exchange the refresh token
for a new access token.

``` http
POST /api/accounts/token/refresh/
```


## Separate JWT Secrets

The project uses separate signing secrets:

``` text
JWT_SECRET_KEY
JWT_REFRESH_SECRET_KEY
```

This provides defense in depth by preventing compromise of one
token-signing secret from automatically compromising the other token
type.


## Logout

``` http
POST /api/accounts/logout/
```

The current refresh token is invalidated/blacklisted so that it cannot
be used to obtain new access tokens.


# Authorization Model

The platform uses two layers of authorization.

## Role-Based Authorization

Controls whether a role can access an endpoint.

Examples:

``` text
Admin → system-wide user management
Analyst → assigned-investor data
Investor → own portfolio data
```

## Object-Level Authorization

Controls which database records the requester can actually access.

For example:

``` text
Investor A
    ↓
Portfolio A
    ↓
Holding A
```

Investor A must not be able to retrieve Investor B's holding simply by
changing:

``` text
/holdings/123/
/holdings/124/
```

The queryset itself is scoped according to the authenticated user and
their role.

This reduces the risk of insecure direct object reference (IDOR).


# Custom Permission Classes

Planned permission classes include:

### `IsOwner`

The authenticated user must own the resource.

Applies to:

-   Portfolio
-   Holding

### `IsAssignedAnalyst`

The requester must:

-   Be an analyst.
-   Be assigned to the resource owner.

### `IsAdminRole`

The requester must have:

``` text
role = admin
```

### `IsOwnerOrAssignedAnalystOrAdmin`

Allows read access when the requester is:

-   The owner.
-   The assigned analyst.
-   An administrator.


# Roles and Permissions

  Action                       Investor   Analyst   Admin
  -------------------------- ---------- --------- -------
  Register / Login                  Yes       Yes     Yes
  View own portfolios               Yes        No     Yes
  View own holdings                 Yes        No     Yes
  View assigned investors            No       Yes     Yes
  View all portfolios                No        No     Yes
  Create own holdings               Yes        No     Yes
  Edit own holdings                 Yes        No     Yes
  Delete own holdings               Yes        No     Yes
  Manual price refresh               No       Yes     Yes
  Trigger ML recomputation           No       Yes     Yes
  Assign analysts                    No        No     Yes
  Manage roles                       No        No     Yes
  System-wide analytics              No        No     Yes


# REST API

All API endpoints are versioned under:

``` text
/api/
```

Except for registration/login/refresh operations, protected endpoints
require a valid JWT access token.


## Accounts

  --------------------------------------------------------------------------------------
  Method            Endpoint                         Description       Access
  ----------------- -------------------------------- ----------------- -----------------
  POST              `/api/accounts/register/`        Register investor Public

  POST              `/api/accounts/login/`           Login and receive Public
                                                     JWT pair          

  POST              `/api/accounts/token/refresh/`   Refresh access    Valid refresh
                                                     token             token

  POST              `/api/accounts/logout/`          Invalidate        Authenticated
                                                     refresh token     

  GET               `/api/accounts/me/`              Current user      Authenticated
                                                     profile           

  PATCH             `/api/accounts/me/`              Update current    Authenticated
                                                     profile           

  GET               `/api/accounts/users/`           List all users    Admin

  PATCH             `/api/accounts/users/{id}/`      Change            Admin
                                                     role/analyst      
                                                     assignment        
  --------------------------------------------------------------------------------------


## Portfolios

  ----------------------------------------------------------------------------------------
  Method            Endpoint                           Description       Access
  ----------------- ---------------------------------- ----------------- -----------------
  GET               `/api/portfolios/`                 List visible      Investor /
                                                       portfolios        Analyst / Admin

  POST              `/api/portfolios/`                 Create portfolio  Investor / Admin

  GET               `/api/portfolios/{id}/`            Portfolio detail  Owner / Analyst /
                                                                         Admin

  PATCH             `/api/portfolios/{id}/`            Update portfolio  Owner / Admin

  DELETE            `/api/portfolios/{id}/`            Delete portfolio  Owner / Admin

  GET               `/api/portfolios/{id}/summary/`    Portfolio         Owner / Analyst /
                                                       value/risk        Admin
                                                       summary           

  GET               `/api/portfolios/{id}/holdings/`   List holdings     Owner / Analyst /
                                                                         Admin

  POST              `/api/portfolios/{id}/holdings/`   Add holding       Owner / Admin
  ----------------------------------------------------------------------------------------


## Holdings

  -----------------------------------------------------------------------------
  Method            Endpoint                Description       Access
  ----------------- ----------------------- ----------------- -----------------
  GET               `/api/holdings/{id}/`   Holding details   Owner / Analyst /
                                                              Admin

  PATCH             `/api/holdings/{id}/`   Update position   Owner / Admin

  DELETE            `/api/holdings/{id}/`   Remove position   Owner / Admin
  -----------------------------------------------------------------------------


## Market Data

  ----------------------------------------------------------------------------------------------
  Method            Endpoint                                 Description       Access
  ----------------- ---------------------------------------- ----------------- -----------------
  GET               `/api/market/prices/{ticker}/`           Latest known      Authenticated
                                                             price             

  GET               `/api/market/prices/{ticker}/history/`   Historical OHLCV  Authenticated

  POST              `/api/market/refresh/{ticker}/`          Queue ticker      Analyst / Admin
                                                             refresh           
  ----------------------------------------------------------------------------------------------


## Analytics

  -----------------------------------------------------------------------------------------------------
  Method            Endpoint                                        Description       Access
  ----------------- ----------------------------------------------- ----------------- -----------------
  GET               `/api/analytics/holdings/{id}/risk/`            Current risk      Owner / Analyst /
                                                                    result            Admin

  GET               `/api/analytics/holdings/{id}/forecast/`        Direction         Owner / Analyst /
                                                                    forecast          Admin

  POST              `/api/analytics/holdings/{id}/recompute/`       Queue ML          Analyst / Admin
                                                                    recomputation     

  GET               `/api/analytics/portfolio/{id}/risk-summary/`   Portfolio risk    Owner / Analyst /
                                                                    breakdown         Admin
  -----------------------------------------------------------------------------------------------------


# Serializers

DRF serializers act as the contract between Django ORM objects and API
clients.

## `UserSerializer`

Exposes:

-   `id`
-   `username`
-   `email`
-   `role`
-   `assigned_analyst`
-   `date_joined`

The password is:

-   Write-only.
-   Validated during creation.
-   Hashed before storage.
-   Never returned in API responses.


## `RegisterSerializer`

Responsible for:

-   Username uniqueness.
-   Email uniqueness.
-   Password confirmation.
-   Password validation.
-   Creating an investor account.

Registration always defaults to:

``` text
role = investor
```


## `LoginSerializer`

Responsible for:

-   Credential validation.
-   Username/email authentication.
-   Token issuing.


## `PortfolioSerializer`

List responses include:

-   `id`
-   `name`
-   `description`
-   `created_at`
-   `holdings_count`
-   `total_value`

Detail responses additionally include nested holding information.


## `HoldingSerializer`

Exposes:

-   `id`
-   `ticker`
-   `quantity`
-   `buy_price`
-   `buy_date`
-   `current_price`
-   `risk_label`
-   `risk_score`
-   `predicted_direction`
-   `prediction_confidence`
-   `last_predicted_at`

ML fields are read-only.

Clients cannot submit their own:

``` text
risk_label
risk_score
predicted_direction
prediction_confidence
```

This prevents users from spoofing analytics results.


## `PriceHistorySerializer`

Read-only representation of:

-   Ticker.
-   Date.
-   Open.
-   High.
-   Low.
-   Close.
-   Volume.


## `RiskSummarySerializer`

Response-only serializer containing:

``` text
portfolio_id
total_value
risk_distribution
average_confidence
```

Example conceptual response:

``` json
{
    "portfolio_id": 1,
    "total_value": 125000.00,
    "risk_distribution": {
        "Low": 4,
        "Medium": 3,
        "High": 1
    },
    "average_confidence": 0.81
}
```


# Celery and Redis

Redis serves three separate purposes.

## 1. Celery Broker

``` text
redis://localhost:6379/0
```

Stores pending Celery tasks.

## 2. Celery Result Backend

``` text
redis://localhost:6379/1
```

Stores Celery task state/results separately from the broker.

## 3. Django Application Cache

The application uses Redis for caching expensive, read-heavy API
responses.


# Scheduled and On-Demand Tasks

## `fetch_daily_prices`

**Trigger:** Celery Beat --- daily after market close.

Responsibilities:

-   Fetch latest OHLCV data.
-   Process tracked tickers.
-   Bulk-insert new `PriceHistory` rows.


## `refresh_single_ticker`

**Trigger:** On-demand API request.

Endpoint:

``` http
POST /api/market/refresh/{ticker}/
```

Available to:

-   Analyst
-   Admin

The operation runs asynchronously instead of blocking the HTTP request.


## `recompute_holding_risk`

**Trigger:** Celery Beat --- nightly.

Responsibilities:

-   Generate latest features.
-   Run Random Forest inference.
-   Update:
    -   `risk_label`
    -   `risk_score`


## `recompute_holding_forecast`

**Trigger:** Celery Beat --- nightly.

Responsibilities:

-   Generate latest features.
-   Run directional model.
-   Update:
    -   `predicted_direction`
    -   `prediction_confidence`


## `recompute_single_holding`

**Trigger:** On-demand.

Endpoint:

``` http
POST /api/analytics/holdings/{id}/recompute/
```

Available to:

-   Analyst
-   Admin


## `retrain_models`

**Trigger:** Weekly/monthly.

Responsibilities:

-   Retrain the Random Forest model.
-   Retrain the Gradient Boosting model.
-   Evaluate the new models.
-   Assign a new `model_version`.
-   Preserve traceability between predictions and the model version that
    generated them.


# Caching Strategy

Portfolio summary and portfolio risk-summary responses are cached in
Redis.

Target TTL:

``` text
~5 minutes
```

Cache invalidation occurs when:

-   A holding is created.
-   A holding is updated.
-   A holding is deleted.
-   ML recomputation completes.

The TTL is therefore a safety net rather than the primary consistency
mechanism.


# Rate Limiting

Manual market-data refresh operations are throttled using a Redis-backed
DRF throttle.

This prevents a single user from repeatedly triggering external
market-data requests.


# Machine Learning Pipeline

The analytics pipeline consumes two primary sources:

``` text
PriceHistory
Holding
```

`PriceHistory` provides historical market information.

`Holding` provides position-specific information such as:

-   Buy price.
-   Quantity.
-   Buy date.


## Feature Engineering

The shared feature set includes:

### Rolling Volatility

Standard deviation of daily returns over:

``` text
30-day window
90-day window
```

### Maximum Drawdown

Measures the maximum decline from a previous peak over a trailing
window.

### Moving Averages

``` text
20-day moving average
50-day moving average
```

### Relative Strength Index

``` text
RSI
```

Used as a technical momentum indicator.

### Trading Volume Trend

Measures the evolution of average trading volume.

### Holding Age

``` text
Current date - buy_date
```

### Unrealized Gain/Loss Percentage

Computed relative to the original buy price.


# Model 1 --- Risk Classification

## Algorithm

``` text
Random Forest Classifier
```

## Target

``` text
risk_label
```

Possible classes:

``` text
Low
Medium
High
```

The risk labels are derived from historical volatility buckets.

## Output

The model writes:

``` text
risk_label
risk_score
```

The `risk_score` represents the model probability associated with the
predicted class.


## Why Random Forest?

Random Forest is appropriate for this project because it:

-   Works well with engineered tabular features.
-   Does not require extremely large datasets.
-   Trains relatively quickly.
-   Can model nonlinear relationships.
-   Provides feature importance information.
-   Is easier to explain than many black-box approaches.

A Logistic Regression model is used as a baseline so that the additional
complexity of Random Forest can be justified using measured evaluation
results rather than assumption.


# Model 2 --- Directional Forecast

## Algorithm

The documented design specifies a gradient-boosting classifier, with the
implementation candidate represented as:

``` text
XGBoost / LightGBM
```

## Target

Binary classification:

``` text
Up
Down
```

The label indicates whether the next trading day's closing price is
higher or lower than the current closing price.

## Output

The model writes:

``` text
predicted_direction
prediction_confidence
```


## Why Direction Instead of Exact Price?

The system intentionally does not attempt to predict:

``` text
"Tomorrow's price will be $187.42."
```

Instead, it predicts:

``` text
"Tomorrow's direction is likely Up."
```

This transforms the problem into a binary classification task that is
easier to validate and discuss responsibly.


# Training Methodology

The models use chronological train/test splitting.

Conceptually:

``` text
Older historical data
        │
        ▼
     Training
        │
        ▼
Later unseen historical data
        │
        ▼
     Testing
```

A random shuffle split is deliberately avoided.

## Why?

Randomly mixing historical observations can introduce **lookahead
bias**, where information from a future period indirectly influences the
training data.

A chronological split better represents the temporal nature of financial
forecasting.


# Model Evaluation

## Risk Classifier

Metrics:

-   Precision per class.
-   Recall per class.
-   F1 score per class.
-   Confusion matrix.

Classes:

``` text
Low
Medium
High
```

## Directional Forecaster

Metrics:

-   Accuracy.
-   F1 score.
-   ROC-AUC.

Model evaluation should be performed on a held-out chronological period
rather than on training data.


# Model Versioning

Models are periodically retrained as new market data becomes available.

Every trained model receives a:

``` text
model_version
```

Predictions can therefore be associated with the exact model version
that produced them.

This makes model behaviour traceable and provides a foundation for:

-   Model comparison.
-   Regression testing.
-   Reproducibility.
-   Future model rollback.
-   Monitoring model performance over time.


# Dataset

The project uses the public Kaggle dataset:

**S&P 500 Stocks --- Daily Historical Data (10 Years)**

Dataset source:

https://www.kaggle.com/datasets/innacampo/s-and-p-500-stocks-daily-historical-data-10-years

The documentation describes the dataset as historical OHLCV data for S&P
500 companies covering approximately 2015--2025.

The source consists of individual CSV files by ticker, for example:

``` text
AAPL.csv
MSFT.csv
...
```

Each file contains fields such as:

``` text
Date
Open
High
Low
Close
```

The ingestion process adds the ticker from the filename and maps the
data into the application's `PriceHistory` representation.


## Dataset-to-Database Mapping

The target schema is:

``` text
ticker
date
open_price
close_price
high_price
low_price
volume
```

Conceptually:

``` text
CSV files
   │
   ├── AAPL.csv
   ├── MSFT.csv
   ├── ...
   │
   ▼
Ticker extraction
   │
   ▼
Data normalization
   │
   ▼
Django ORM
   │
   ▼
PriceHistory
   │
   ▼
PostgreSQL
```

The historical dataset acts as a one-time backfill source, while the
Celery ingestion system is intended to handle ongoing market-data
updates.


## Why Ten Years of Data?

The documented ML feature set uses:

-   30-day rolling volatility.
-   90-day rolling volatility.
-   20-day moving averages.
-   50-day moving averages.
-   RSI.
-   Drawdown.
-   Volume trends.

These features require sufficient historical observations before they
become usable.

Ten years also provides a substantial chronological span for:

-   Training.
-   Validation.
-   Recent holdout testing.
-   Cross-sectional learning across multiple S&P 500 tickers.


# Environment Configuration

Environment-specific settings should be stored in a `.env` file.

The `.env` file must **never be committed to Git**.

Example configuration:

``` env
DATABASE_NAME=stock_risk_prediction_db
DATABASE_USER=django_user
DATABASE_PASSWORD=your-secret-password
DATABASE_HOST=localhost
DATABASE_PORT=5432

JWT_SECRET_KEY=your-jwt-secret
JWT_REFRESH_SECRET_KEY=your-refresh-secret

ACCESS_TOKEN_LIFETIME_MINUTES=15
REFRESH_TOKEN_LIFETIME_DAYS=7

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### Important

Never commit:

``` text
.env
database passwords
Django SECRET_KEY
JWT secrets
API credentials
private tokens
```


# Project Directory Structure

The documented target architecture is:

``` text
stock-portfolio-tracker-with-risk-prediction-engine/
│
├── manage.py
│
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── accounts/
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
│
├── portfolios/
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
│
├── market_data/
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── tasks.py
│   └── urls.py
│
├── analytics/
│   ├── migrations/
│   ├── feature_engineering.py
│   ├── models/
│   ├── training/
│   ├── tasks.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
├── core/
│   ├── permissions.py
│   ├── pagination.py
│   ├── exceptions.py
│   └── throttles.py
│
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── .env
├── .gitignore
└── README.md
```

> The directory structure above represents the target architecture
> described in the project documentation. The repository may initially
> contain only the Django project scaffold while the remaining
> applications are implemented incrementally.


# Installation and Local Development

## 1. Clone the Repository

``` bash
git clone https://github.com/DJamesSmith/stock-portfolio-tracker-with-risk-prediction-engine.git
cd stock-portfolio-tracker-with-risk-prediction-engine
```


## 2. Create a Virtual Environment

macOS/Linux:

``` bash
python3 -m venv venv
source venv/bin/activate
```

Windows:

``` powershell
python -m venv venv
venv\Scripts\activate
```


## 3. Upgrade pip

``` bash
python -m pip install --upgrade pip
```


## 4. Install Dependencies

Once the dependency file is created:

``` bash
pip install -r requirements.txt
```

If the project uses separated requirement files:

``` bash
pip install -r requirements/development.txt
```


## 5. Configure Environment Variables

Create:

``` text
.env
```

and provide the required database, JWT, Redis, and application settings.


# Database Setup

Create the PostgreSQL database:

``` text
stock_risk_prediction_db
```

Create the PostgreSQL role:

``` text
django_user
```

Then configure the credentials in `.env`.

Run:

``` bash
python manage.py makemigrations
python manage.py migrate
```

Create an administrator:

``` bash
python manage.py createsuperuser
```


# Running Django

Start the development server:

``` bash
python manage.py runserver
```

The development API will normally be available at:

``` text
http://127.0.0.1:8000/
```

The Django REST Framework browsable API can be used during development
and testing.


# Running Redis

Redis must be available for Celery and caching.

Verify Redis:

``` bash
redis-cli ping
```

Expected response:

``` text
PONG
```


# Running Celery

Start a Celery worker from the project root:

``` bash
celery -A config worker --loglevel=info
```

Start Celery Beat separately:

``` bash
celery -A config beat --loglevel=info
```

> Replace `config` with the actual Django project package if the project
> package remains `stock_risk_engine` during the initial implementation.

The worker handles asynchronous tasks while Celery Beat schedules
recurring jobs.


# Authentication Flow

The intended lifecycle is:

``` text
1. Register
      ↓
2. Login
      ↓
3. Receive access + refresh tokens
      ↓
4. Send access token with API requests
      ↓
5. Access token expires
      ↓
6. Send refresh token
      ↓
7. Receive new access token
      ↓
8. Continue API usage
      ↓
9. Logout
      ↓
10. Refresh token invalidated
```


# End-to-End Workflow

A representative user workflow is:

### Step 1 --- Investor Registration

``` http
POST /api/accounts/register/
```

The new account is created as an investor.

### Step 2 --- Login

``` http
POST /api/accounts/login/
```

The system returns:

``` text
access_token
refresh_token
```

### Step 3 --- Create Portfolio

``` http
POST /api/portfolios/
```

The investor creates a portfolio.

### Step 4 --- Add Holding

The investor specifies:

``` text
ticker
quantity
buy_price
buy_date
```

### Step 5 --- Market Data Check

If recent `PriceHistory` data is unavailable, the system queues an
asynchronous ingestion task rather than forcing the user to wait for an
external market-data request.

### Step 6 --- ML Processing

Scheduled Celery tasks:

``` text
recompute_holding_risk
recompute_holding_forecast
```

engineer features and generate:

``` text
risk_label
risk_score
predicted_direction
prediction_confidence
```

### Step 7 --- Portfolio Summary

The investor requests:

``` http
GET /api/portfolios/{id}/summary/
```

The system checks Redis first.

If a valid cached result exists:

``` text
Redis → Response
```

Otherwise:

``` text
API
 ↓
Django ORM
 ↓
PostgreSQL
 ↓
Aggregation
 ↓
Redis cache
 ↓
Response
```

### Step 8 --- Analyst Access

An assigned analyst can view the investor's portfolio in a read-only
capacity.

The access is enforced by:

``` text
IsAssignedAnalyst
```

rather than special-casing individual views.


# Security Considerations

Security is a core part of the architecture.

## Password Security

Passwords are never stored as plaintext.

Django's standard password hashing and validation mechanisms are reused
with the custom user model.


## JWT Security

Access tokens are intentionally short-lived:

``` text
15 minutes
```

Refresh tokens have a longer lifetime:

``` text
7 days
```

Separate signing secrets are used for the two token types.


## Object-Level Authorization

Authorization is applied at the queryset/resource level.

This prevents users from accessing another user's resources by guessing
IDs.


## Rate Limiting

Registration, login, and manual market-data refresh operations are
throttled.


## CORS

CORS should be restricted to known client origins.

It should not be configured as an unrestricted:

``` text
Allow-All
```

policy in production.


## Secrets

Secrets must be loaded through environment configuration.

Never commit:

``` text
.env
```

or credentials to the repository.


# Performance and Non-Functional Considerations

## Database Indexes

The design specifies indexes for frequently queried fields, including:

``` text
PriceHistory(ticker, date)
Holding(portfolio_id)
Portfolio(user_id)
```

These indexes support the join-heavy queries used by portfolio and
analytics endpoints.


## Query Optimization

Django ORM optimization should use:

``` python
select_related()
prefetch_related()
```

where appropriate.

For aggregation:

``` python
values()
annotate()
```

should be preferred over retrieving unnecessary rows into application
memory.


## N+1 Query Prevention

Nested portfolio/holding API responses should be designed with
appropriate queryset optimization to avoid N+1 query behaviour.


## Pagination

List endpoints should be paginated to:

-   Limit response size.
-   Reduce database load.
-   Improve API performance.
-   Reduce mobile data usage.


## Background Processing

Expensive operations should not run synchronously inside HTTP requests.

Examples:

``` text
Market data ingestion
ML inference
Model retraining
Large aggregation tasks
```

These are candidates for Celery execution.


# Flutter Integration Readiness

The backend is designed to support a future Flutter application.

The planned mobile client can consume the existing REST API for:

### Authentication

``` text
Register
Login
Token Refresh
Logout
Profile
```

### Portfolio

``` text
Portfolio list
Portfolio detail
Portfolio summary
Holdings
```

### Analytics

``` text
Risk label
Risk score
Predicted direction
Prediction confidence
```

### Market Data

``` text
Current price
Historical price series
```

The backend should not require architectural changes simply because the
client changes from Postman/web to Flutter.

A Flutter implementation can use secure client-side token storage rather
than insecure browser-style local storage.


# Future Scope

The documented future roadmap includes:

## Push Notifications

Use Firebase Cloud Messaging to notify users when:

-   A holding's risk level changes.
-   A forecast crosses a confidence threshold.


## Real-Time Price Updates

Potential implementation:

``` text
Django Channels
WebSockets
```

This could replace periodic polling for selected live-data use cases.


## Sector-Level Analytics

Potential features:

-   Sector exposure.
-   Sector concentration.
-   Sector risk.
-   Sector diversification.


## Portfolio Diversification Score

Introduce a portfolio-level diversification metric based on:

-   Number of assets.
-   Sector exposure.
-   Concentration.
-   Risk distribution.


## Portfolio Rebalancing

Use existing risk information to generate potential rebalancing
suggestions.


## LSTM Forecasting

An LSTM-based model may be introduced as a stretch goal.

It should be treated as a comparison against the existing simpler
gradient-boosting approach rather than automatically replacing it.

The purpose would be to determine whether additional model complexity
provides a measurable improvement.


## Docker

Containerization using:

``` text
Docker
Docker Compose
```

may be introduced when the project moves toward a shared or
production-style deployment environment.


# Development Roadmap

The recommended implementation sequence is:

``` text
Phase 1
Django project configuration
        ↓
Phase 2
PostgreSQL integration
        ↓
Phase 3
Custom User model
        ↓
Phase 4
JWT authentication
        ↓
Phase 5
Role-based permissions
        ↓
Phase 6
Portfolio + Holding models
        ↓
Phase 7
Market data + PriceHistory
        ↓
Phase 8
REST API endpoints
        ↓
Phase 9
Redis + Celery
        ↓
Phase 10
Historical dataset ingestion
        ↓
Phase 11
Feature engineering
        ↓
Phase 12
Risk classification model
        ↓
Phase 13
Directional forecasting model
        ↓
Phase 14
Scheduled ML inference
        ↓
Phase 15
Caching + throttling + optimization
        ↓
Phase 16
API testing
        ↓
Phase 17
Flutter client
        ↓
Phase 18
Production deployment
```


# Current Implementation Status

The project documentation describes the complete target architecture,
while the implementation is being developed incrementally.

The initial Django project scaffold is created using:

``` bash
django-admin startproject stock_risk_engine
```

The repository should therefore be treated as an evolving implementation
of the architecture documented above.

As development progresses, this README should be updated to reflect:

-   Implemented applications.
-   Implemented endpoints.
-   Database migrations.
-   ML models.
-   Celery tasks.
-   Tests.
-   Deployment configuration.
-   Flutter integration.

This distinction is important: **architecture/documentation should
describe the intended system, while implementation status should
accurately reflect what currently exists in the repository.**


# Machine Learning Disclaimer

The risk classifications and directional forecasts generated by this
project are machine-learning outputs based on historical market data and
engineered technical features.

They are intended for:

-   Educational purposes.
-   Software engineering demonstration.
-   Machine-learning experimentation.
-   Portfolio analytics research.

They are **not financial advice** and should not be treated as
guaranteed predictions of future market behaviour.

Historical market performance does not guarantee future results.

# License

A license has not been specified in the project documentation.

Add an appropriate license before treating this repository as an
open-source project.
