# Personal Finance Tracker — Project Spec

**Author:** [Your Name]  
**Date:** July 2026  
**Status:** Draft  

---

## Overview

A personal finance tracker that ingests bank statement CSV exports, automatically categorizes transactions using AI, and identifies recurring payments and subscriptions. Built as a full-stack web app using the technologies covered in the bootcamp: Python, JavaScript, HTML, PostgreSQL, Docker, and external API keys.

---

## Problem

Most people have no easy way to understand their spending patterns without manually going through bank statements or paying for a service like Mint or YNAB. This tool lets a user drop in a CSV export from their bank and immediately get an AI-categorized breakdown of their finances — all running locally in Docker.

---

## Goals

- Parse standard bank statement CSV exports into a normalized format
- Automatically categorize transactions using the OpenAI API
- Detect recurring payments and tag them as subscriptions
- Store all transaction data in a PostgreSQL database
- Display a monthly spending dashboard with charts
- Allow users to manually reassign categories
- Run the entire stack with a single `docker-compose up` command

## Non-Goals

- No user accounts or authentication (single user, local use)
- No live bank API connections (Plaid, etc.)
- No mobile support
- No deployment to the cloud

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Frontend | HTML + CSS + Vanilla JS | Covers bootcamp JS/HTML requirement, keeps it simple |
| Backend | Python + FastAPI | Clean REST API, auto-generates `/docs` page for demo |
| Database | PostgreSQL | Industry standard, runs in Docker |
| ORM | SQLAlchemy | Manages DB models and queries in Python |
| Containerization | Docker + docker-compose | Full stack runs in one command |
| External API | OpenAI API | Smart AI categorization via API key in `.env` |
| Charts | Chart.js | Lightweight, works with vanilla JS, no build step needed |

---

## Architecture

Three Docker containers managed by docker-compose:

```
┌─────────────────┐     REST API      ┌─────────────────┐     SQL      ┌─────────────┐
│                 │ ───────────────►  │                 │ ──────────►  │             │
│  Frontend       │                   │  Backend        │              │  PostgreSQL  │
│  nginx + HTML   │ ◄───────────────  │  FastAPI        │ ◄──────────  │  Database   │
│  port 3000      │     JSON          │  port 8000      │              │  port 5432  │
│                 │                   │       │          │              │             │
└─────────────────┘                   └───────┼──────────┘              └─────────────┘
                                              │
                                              ▼ OPENAI_API_KEY
                                       OpenAI API
                                       (categorization)
```

---

## Data Model

### Transaction Table

```
transactions
  id              UUID        primary key
  date            DATE        transaction date
  description     TEXT        raw merchant description from the bank
  amount          NUMERIC     positive = credit, negative = debit
  category        TEXT        assigned category
  is_recurring    BOOLEAN     flagged as recurring payment
  frequency       TEXT        "weekly" | "biweekly" | "monthly" | "annual" | null
  tags            TEXT[]      array of tags e.g. ["subscription"]
  created_at      TIMESTAMP   when the record was inserted
```

### Categories Table

```
categories
  id              UUID        primary key
  name            TEXT        category name
  keywords        TEXT[]      merchant names mapped to this category (cache)
```

---

## Features

### 1. CSV Upload and Parsing

User uploads a CSV exported from their bank via a file input on the upload page. The backend parses and normalizes it into the Transaction format.

**Supported formats:**
- Chase (columns: date, description, amount, type, balance)
- Bank of America (columns: date, description, reference, credits, debits)
- Generic fallback — user maps columns manually via dropdowns if their bank format isn't recognized

**Normalization steps:**
- Standardize date format to YYYY-MM-DD
- Merge separate credit/debit columns into a single signed amount
- Strip extra whitespace from descriptions
- Deduplicate rows if the user uploads overlapping date ranges (match on date + description + amount)

**API endpoint:** `POST /upload`

---

### 2. AI Categorization (OpenAI API)

Instead of a static keyword list, transaction descriptions are sent to the OpenAI API which returns a category. This handles the messy, abbreviated descriptions banks actually export.

**How it works:**
1. On upload, extract the unique merchant names from the parsed transactions
2. For each merchant not already in the categories cache, call the OpenAI API
3. Ask it to return one of the predefined category names
4. Save the merchant → category mapping to the database (so the same merchant is never re-sent)
5. Apply the cached category to all matching transactions

**Prompt sent to OpenAI:**
```
You are a personal finance categorizer. Given a bank transaction description,
return exactly one of these categories:

Food & Dining, Groceries, Transport, Subscriptions, Shopping,
Health, Utilities, Travel, Entertainment, Uncategorized

Transaction description: "{description}"

Return only the category name, nothing else.
```

**API key:** Stored in `.env` as `OPENAI_API_KEY`, loaded via python-dotenv. Never committed to git.

**Cost note:** Caching means you only pay per unique merchant, not per transaction.

---

### 3. Recurring Payment Detection

Identifies transactions that appear on a regular schedule and tags them as subscriptions.

**Algorithm:**
1. Group all transactions by normalized merchant name (lowercase, strip trailing digits/punctuation)
2. For each merchant appearing 2 or more times, calculate intervals between occurrences in days
3. Classify the interval:
   - 6–8 days → weekly
   - 13–16 days → biweekly
   - 28–32 days → monthly
   - 360–370 days → annual
4. If amounts across occurrences are within ±$1.00, confirm as recurring
5. Set `is_recurring = true`, set `frequency`, add `"subscription"` to `tags`

**Subscriptions view:** Lists all recurring transactions with merchant name, amount, frequency, and estimated monthly cost (annuals ÷ 12, weeklies × 4.33).

---

### 4. Dashboard

Main page after uploading a statement. All data fetched from the backend API.

**Sections:**

**Summary bar (top)**
- Total spent this month
- Total credited this month
- Number of active subscriptions
- Estimated monthly subscription cost

**Spending by category chart**
- Donut or horizontal bar chart showing % and dollar amount per category
- Built with Chart.js

**Subscriptions list**
- Table: merchant name, amount, frequency, monthly equivalent
- Sorted by monthly cost descending

**Transaction table (bottom)**
- Full list of transactions
- Columns: date, description, category, amount
- Filterable by category via dropdown
- Sortable by date or amount
- Click a category to reassign it (opens a dropdown inline)

---

### 5. Manual Category Override

User can click the category on any transaction in the table and change it via an inline dropdown. Change is saved to the database immediately via a `PUT` request.

---

## API Endpoints

```
POST   /upload                  Upload a CSV file, parse and store transactions
GET    /transactions            List all transactions (supports ?category= filter)
PUT    /transactions/{id}       Update the category of a transaction
GET    /summary                 Spending totals grouped by category
GET    /subscriptions           List all recurring/subscription transactions
DELETE /transactions            Clear all transactions (for re-uploading a new file)
```

---

## Project Structure

```
finance-tracker/
├── docker-compose.yml
├── .env                            # OPENAI_API_KEY, DATABASE_URL (never commit this)
├── .env.example                    # Template with empty values (commit this)
├── .gitignore
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                     # FastAPI app, route definitions
│   ├── parser.py                   # CSV ingestion and normalization
│   ├── categorizer.py              # OpenAI API calls, caching logic
│   ├── recurring.py                # Recurring payment detection algorithm
│   ├── models.py                   # SQLAlchemy DB models
│   └── database.py                 # DB connection setup
│
└── frontend/
    ├── Dockerfile                  # nginx config
    ├── index.html                  # Dashboard
    ├── upload.html                 # CSV upload page
    └── js/
        ├── app.js                  # API fetch calls, table rendering
        └── charts.js               # Chart.js setup and rendering
```

---

## Docker Setup

**docker-compose.yml** runs three services:

```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: finance
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - db

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

---

## Environment Variables

```
# .env (never commit)
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://user:password@db:5432/finance
```

---

## Build Plan

### Phase 1 — Backend Foundation
- [ ] Set up docker-compose with backend, frontend, and PostgreSQL containers
- [ ] Define SQLAlchemy models and run initial DB migration
- [ ] Build CSV parser with normalization for Chase and BofA formats
- [ ] `POST /upload` endpoint — parses CSV and stores transactions in DB
- [ ] `GET /transactions` endpoint — returns stored transactions as JSON

### Phase 2 — Categorization + Recurring Detection
- [ ] Integrate OpenAI API for categorization
- [ ] Cache merchant → category mappings in the database
- [ ] Build recurring payment detection algorithm
- [ ] `GET /subscriptions` endpoint
- [ ] `GET /summary` endpoint — totals by category

### Phase 3 — Frontend
- [ ] Upload page with CSV file input, calls `POST /upload`
- [ ] Dashboard page fetches and renders summary data
- [ ] Transaction table with category filter and sort
- [ ] Chart.js donut chart for spending by category
- [ ] Inline category override — `PUT /transactions/{id}`

### Phase 4 — Polish and Demo Prep
- [ ] Add sample CSV files for demo use
- [ ] Handle error states in the UI (bad CSV format, API failure)
- [ ] Add loading states while data is being fetched
- [ ] Write a README with setup instructions
- [ ] Test full flow end-to-end in Docker

---

## Stretch Goals (if time allows)

- Upload multiple months and show month-over-month comparison chart
- Budget targets per category with a progress bar showing over/under
- PDF statement parsing via pdfplumber
- Export categorized transactions back to a clean CSV
- Search bar in the transaction table
- Dark mode toggle

---

## Open Questions

- Which bank formats should be supported on day one? Recommend Chase + generic fallback.
- Use OpenAI GPT-3.5-turbo (cheaper) or GPT-4o-mini for categorization?
- Should the delete/reset endpoint be protected in any way, or is it fine as-is for a local tool?
