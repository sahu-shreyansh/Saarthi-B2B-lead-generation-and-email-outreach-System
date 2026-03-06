# Saarthi Revenue OS

**AI-Powered B2B Lead Generation & Outreach Platform**

Saarthi automates the entire outbound sales lifecycle — from intelligent lead discovery and AI scoring, to autonomous cold outreach and inbox intent classification.

---

## Architecture Overview

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 16 + React | Dashboard, Campaigns, Inbox, Meetings, Settings |
| **Backend** | FastAPI + SQLAlchemy | REST API, Auth, Multi-tenant isolation |
| **Workers** | Celery + Redis | Discovery, Email generation, Inbox classification |
| **Database** | PostgreSQL 15 | Leads, Campaigns, Inbox threads, Meetings |
| **AI Gateway** | OpenRouter (GPT-4o / Claude 3.5) | Lead scoring, Email personalization, Intent classification |
| **Scraping** | Apify Actors + SerpAPI | Lead discovery from Google Search + Website crawling |
| **Email Sending** | Resend / SendGrid / SMTP | Automated cold outreach |

---

## 🚀 Quick Start with Docker

### Prerequisites

- [Docker Engine & Docker Compose V2](https://docs.docker.com/get-docker/)
- API Keys: **OpenRouter**, **Apify**, **SerpAPI**
- (Optional) **Resend** or **SendGrid** for email sending

### 1. Clone & Configure

```bash
git clone <repo-url>
cd saarthi-revenue-os

# Copy and fill in environment variables
cp backend/.env.example backend/.env
```

Edit `backend/.env` with your credentials:

```ini
# PostgreSQL (auto-configured in Docker)
DATABASE_URL=postgresql://saarthi:saarthi@db:5432/saarthi

# Redis (auto-configured in Docker)
REDIS_URL=redis://redis:6379/0

# Auth
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AI Providers
OPENROUTER_API_KEY=sk-or-v1-...

# Scraping
APIFY_TOKEN=apify_api_...
SERPAPI_KEY=...

# Email Sending (choose one)
EMAIL_PROVIDER=resend    # or "sendgrid" / "smtp"
RESEND_API_KEY=re_...
SENDGRID_API_KEY=SG...

# Frontend URL
FRONTEND_URL=http://localhost:3000
```

### 2. Build & Launch

```bash
docker-compose up -d --build
```

This starts 5 services:

| Service | URL | Description |
|---------|-----|-------------|
| `frontend` | http://localhost:3000 | Next.js web app |
| `backend` | http://localhost:8000 | FastAPI REST API |
| `db` | Port 5432 | PostgreSQL database |
| `redis` | Port 6379 | Celery message broker |
| `celery_worker` | — | Background task worker |

### 3. Initialize Database

On first run, apply database migrations:

```bash
docker-compose exec backend alembic upgrade head
```

### 4. Verify Everything is Running

```bash
# Check service health
docker-compose ps

# View backend API docs
open http://localhost:8000/docs

# Stream logs
docker-compose logs -f
```

---

## 💻 Local Development

### Backend

Requires Python 3.12+, PostgreSQL, and Redis running locally.

```bash
cd backend

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000

# In a separate terminal — Start Celery Worker
celery -A app.workers.celery_app worker --loglevel=info

# Optional: Start Celery Beat for scheduled tasks
celery -A app.workers.celery_app beat --loglevel=info
```

### Frontend

Requires Node.js 20+.

```bash
cd frontend

npm install
npm run dev
```

The frontend dev server runs on **http://localhost:3000** and automatically proxies all `/api/*` requests to the backend at `http://localhost:8000` (configured in `next.config.js`).

---

## 🔗 API Endpoints Reference

All API endpoints are prefixed with `/api` when accessed from the frontend (via Next.js rewrite proxy).

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register new user + organization |
| `POST` | `/auth/login` | Login, returns JWT token |
| `GET` | `/auth/me` | Get current user + org details |

### Leads

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/leads` | List leads (filter by industry, status, search) |
| `POST` | `/leads` | Create single lead |
| `PATCH` | `/leads/{id}` | Update lead |
| `DELETE` | `/leads/{id}` | Delete lead |
| `POST` | `/leads/bulk-create` | Bulk import leads |

### Campaigns

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/campaigns` | List campaigns |
| `POST` | `/campaigns` | Create campaign |
| `GET` | `/campaigns/{id}` | Get campaign details |
| `PATCH` | `/campaigns/{id}` | Update campaign (template, score threshold, limits) |
| `POST` | `/campaigns/{id}/start` | Activate campaign + start Celery pipeline |
| `POST` | `/campaigns/{id}/pause` | Pause active campaign |
| `GET` | `/campaigns/{id}/stats` | Get email stats (sent, opened, replied, bounced) |
| `GET` | `/campaigns/{id}/emails` | List all generated emails for campaign |

### AI Lead Discovery

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/discovery/run` | Start background lead discovery (SerpAPI + Apify) |
| `GET` | `/discovery/status/{task_id}` | Poll discovery job status |

### AI Intelligence

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/intelligence/score` | Trigger AI scoring for a single lead |
| `POST` | `/intelligence/enrich` | Trigger website metadata extraction |
| `GET` | `/intelligence/score/{lead_id}` | Get latest score for a lead |

### Inbox

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/inbox` | List inbox threads (filter by status) |
| `GET` | `/inbox/{id}/messages` | Get messages in a thread |
| `POST` | `/inbox/{id}/reply` | Trigger AI auto-reply |
| `POST` | `/inbox/{id}/classify` | Run intent classification |
| `POST` | `/inbox/process` | Fetch new messages from connected email accounts |

### Meetings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/meetings` | List all meetings |
| `POST` | `/meetings` | Create meeting |
| `PATCH` | `/meetings/{id}` | Update/reschedule meeting |
| `DELETE` | `/meetings/{id}` | Cancel meeting |
| `POST` | `/meetings/{id}/send-confirmation` | Send confirmation email |

### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/dashboard/metrics` | Key KPIs: `total_leads`, `qualified_leads`, `active_campaigns`, `emails_sent`, `replies_received`, `meetings_booked`, `conversion_rate` |
| `GET` | `/dashboard/lead-growth` | Lead growth time series |
| `GET` | `/dashboard/email-performance` | Email funnel metrics |
| `GET` | `/dashboard/recent-activity` | Activity feed |
| `GET` | `/dashboard/ai-usage` | Token consumption and cost tracking |

### Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/settings` | Get organization settings (integrations, notification preferences) |
| `PATCH` | `/settings` | Update general settings (AI auto-reply, slack webhooks, etc.) |
| `POST` | `/settings/integrations/email` | Configure email provider (SMTP/SendGrid/Resend) with credentials |
| `POST` | `/settings/integrations/calendar` | Configure calendar provider (Google/Calendly) with credentials |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/tasks/{task_id}` | Poll background Celery task status |

---

## 🤖 AI Pipelines

### Lead Discovery Pipeline
1. `POST /discovery/run` → Spawns `run_discovery_task` Celery job
2. SerpAPI queries Google for companies matching `industry` + `location`
3. Apify crawls company websites for metadata  
4. Leads are stored in database with `status=new`  
5. Frontend polls `/tasks/{task_id}` for progress

### Lead Scoring Pipeline
1. `POST /intelligence/score` → Spawns `score_lead_task` Celery job
2. OpenRouter GPT-4o / Claude 3.5 scores lead against B2B SaaS ICP criteria (0–100)
3. Score + metadata written back to the `leads` table

### Campaign Email Pipeline
1. `POST /campaigns/{id}/start` → Spawns `run_campaign` Celery job
2. Campaign worker filters leads by `score >= target_score`
3. OpenRouter generates personalized cold email from `email_template`
4. Email sent via configured provider (Resend / SendGrid / SMTP)
5. `CampaignEmail` records created + `campaign.stats` JSONB updated

### Inbox Classification Pipeline
1. `POST /inbox/process` → fetches new emails from connected accounts
2. `POST /inbox/{id}/classify` → OpenRouter classifies reply intent (POSITIVE / NEGATIVE / MEETING_REQUEST / UNSUBSCRIBE)
3. `POST /inbox/{id}/reply` → Auto-generates and sends AI reply if intent matches
4. If `MEETING_REQUEST` → auto-creates Meeting entry

---

## 🗄 Database Schema

### Core Tables

```
organizations        → Multi-tenant isolation root
users               → Auth accounts, linked to org
leads               → company_name, contact_email, contact_name, score, status, metadata (JSONB)
lead_sources        → Configuration for discovery/import sources (NEW)
campaigns           → name, email_template, target_score, daily_limit, status, stats (JSONB)
campaign_emails     → Per-email records with status (QUEUED/SENT/BOUNCED)
email_events        → Granular tracking for opens, clicks, bounces (NEW)
inbox_threads       → Grouped conversations per lead/email
inbox_messages      → Individual messages with intent classification
meetings            → Scheduled calls with status lifecycle
ai_usage_logs       → LLM token usage + cost tracking
worker_logs         → Celery task execution logs
```

---

## 🔐 Multi-Tenant Security

Every database query is automatically scoped to `organization_id` via:
1. **JWT Auth** → `get_current_user_and_org` dependency extracts org from token
2. **OrgIsolationMiddleware** → Blocks cross-tenant data access at middleware level
3. **Rate Limiting** → Redis token bucket per user/IP

---

## 🧪 Testing

```bash
# Run backend test suite
docker-compose exec backend pytest tests/ -v

# Run with coverage
docker-compose exec backend pytest tests/ --cov=app --cov-report=html
```

---

## 📁 Project Structure

```
saarthi-revenue-os/
├── backend/
│   ├── app/
│   │   ├── core/          # Settings, Auth, Dependencies
│   │   ├── database/      # SQLAlchemy models + Alembic migrations
│   │   ├── middleware/    # Org isolation, Rate limiting
│   │   ├── routers/       # 14 FastAPI router modules
│   │   ├── services/      # AI, Email sending, Scoring services
│   │   └── tasks/         # Celery pipeline tasks
│   ├── alembic/           # Database migrations
│   ├── tests/             # PyTest test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js App Router pages
│   │   ├── components/    # Shared UI components (Sidebar, Topbar)
│   │   ├── hooks/         # React Query data hooks
│   │   ├── lib/           # API client, Auth token management
│   │   └── types/         # TypeScript interfaces
│   └── next.config.js     # API proxy rewrite rules
├── docker-compose.yml
└── README.md
```

---

## 🛠 Troubleshooting

### Backend won't start
```bash
# Check backend logs
docker-compose logs backend

# Common issues:
# - DATABASE_URL wrong → Check .env
# - Redis not running → docker-compose up redis
# - Migrations not run → docker-compose exec backend alembic upgrade head
```

### Frontend API calls failing
```bash
# Check that backend is accessible
curl http://localhost:8000/health

# Frontend proxies /api/* → localhost:8000/*
# Verify next.config.js has the rewrite rule
```

### Celery tasks not running
```bash
# Check celery worker logs
docker-compose logs celery_worker

# Common issues:
# - REDIS_URL mismatch
# - Missing OPENROUTER_API_KEY for AI tasks
# - Celery app import errors → Check app.workers.celery_app
```

### Database connection errors
```bash
# Connect to postgres directly
docker-compose exec db psql -U saarthi -d saarthi

# Re-run migrations
docker-compose exec backend alembic upgrade head
```
