# 🚀 SAARTHI – FULL PRODUCTION BACKEND EXECUTION SPEC

## ⚠️ READ THIS CAREFULLY

You are building a **VC-scale SaaS cold outreach platform**.

This is NOT a demo.
This is NOT an MVP hack.
This is production-grade architecture.

You must:

* Think like a senior SaaS architect
* Think multi-tenant
* Think security-first
* Think provider abstraction
* Never cut corners
* Never simplify logic unless explicitly told
* Ask for clarification before making assumptions
* Do not skip error handling
* Do not ignore scalability

If something is ambiguous — ASK.

---

# 🏢 PRODUCT OVERVIEW

Product Name: Saarthi
Type: Multi-tenant SaaS
Model: Organization-based
Join Policy: Default INVITE_ONLY
Email Providers: Gmail + Outlook (Microsoft Graph)
Campaign Model: Multi-sender rotation
Inbox: Toggleable (Personal / Shared)
Billing: Stripe (per seat + monthly email cap)
Database: PostgreSQL
Backend: FastAPI
Auth: JWT + Google SSO + Microsoft SSO
Workers: Background jobs (reply detection + followups)

---

# 🔐 CORE RULES (NON-NEGOTIABLE)

1. Every table (except organizations) MUST include org_id.
2. org_id must NEVER be accepted from frontend.
3. org isolation enforced via middleware.
4. outreach_logs must be append-only.
5. thread_id must always be captured after send.
6. Refresh tokens must be AES encrypted.
7. Provider abstraction layer must exist.
8. Rotation must be round-robin and stateful.
9. Stripe webhook signature must be verified.
10. All sending must check usage limits first.

---

# 🗂 REQUIRED BACKEND FOLDER STRUCTURE

Generate this exact structure:

```
backend/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── middleware/
│   │   ├── auth_middleware.py
│   │   └── org_isolation.py
│   │
│   ├── models/
│   │   ├── organization.py
│   │   ├── user.py
│   │   ├── sending_account.py
│   │   ├── campaign.py
│   │   ├── campaign_sender.py
│   │   ├── lead.py
│   │   ├── outreach_log.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── subscription.py
│   │   ├── usage_tracking.py
│   │   ├── invite.py
│   │   └── pending_request.py
│   │
│   ├── schemas/
│   ├── routers/
│   │   ├── auth.py
│   │   ├── organizations.py
│   │   ├── users.py
│   │   ├── sending_accounts.py
│   │   ├── campaigns.py
│   │   ├── leads.py
│   │   ├── outreach.py
│   │   ├── inbox.py
│   │   ├── billing.py
│   │   └── webhooks.py
│   │
│   ├── services/
│   │   ├── rotation_service.py
│   │   ├── usage_service.py
│   │   ├── stripe_service.py
│   │   └── encryption_service.py
│   │
│   ├── providers/
│   │   ├── base.py
│   │   ├── gmail.py
│   │   ├── outlook.py
│   │   └── factory.py
│   │
│   ├── workers/
│   │   ├── reply_detector.py
│   │   └── followup_engine.py
│   │
│   └── utils/
│
├── alembic/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

No simplifications allowed.

---

# 🗄 DATABASE SCHEMA (POSTGRESQL)

Generate full SQL migrations.

## organizations

* id (UUID PK)
* name
* primary_domain
* join_policy DEFAULT 'INVITE_ONLY'
* created_at

## users

* id (UUID)
* org_id (FK)
* email (unique within org)
* password_hash (nullable)
* role (OWNER, ADMIN, MEMBER, VIEWER)
* auth_provider (local, google, microsoft)
* is_active
* created_at

## sending_accounts

* id
* org_id
* user_id
* provider (gmail/outlook)
* email
* refresh_token (encrypted)
* token_expiry
* is_shared
* is_active
* daily_limit
* created_at

## campaigns

* id
* org_id
* name
* status (active/paused)
* sequence_json (JSONB)
* last_rotation_index INT DEFAULT 0
* created_by
* created_at

## campaign_sending_accounts

* campaign_id
* sending_account_id
* rotation_order
* is_active

## leads

* id
* org_id
* campaign_id
* name
* company
* email
* status
* created_at

## outreach_logs (APPEND ONLY)

* id
* org_id
* campaign_id
* lead_id
* sending_account_id
* provider
* sequence_step
* thread_id
* message_id
* sent_at
* reply_status (NO_REPLY/REPLIED)
* followup_status (PENDING/STOPPED)
* next_followup_due

## conversations

* id
* org_id
* campaign_id
* lead_id
* sending_account_id
* provider
* thread_id
* last_message_at

## messages

* id
* conversation_id
* sender_type (USER/LEAD)
* body
* sent_at

## subscriptions

* id
* org_id
* stripe_customer_id
* stripe_subscription_id
* plan_type
* monthly_limit
* seat_limit
* status
* current_period_end

## usage_tracking

* id
* org_id
* month
* emails_sent

---

# 🔁 ROTATION LOGIC (MANDATORY IMPLEMENTATION)

Implement Round Robin:

1. Fetch campaign_sending_accounts ordered by rotation_order
2. Filter active accounts
3. Skip accounts exceeding daily_limit
4. Use last_rotation_index
5. Increment and persist

Must be atomic (transaction safe).

---

# 📧 PROVIDER ABSTRACTION (MANDATORY)

Create BaseProvider class with:

* send_email()
* fetch_replies()
* refresh_token()
* extract_thread_id()

Gmail:

* threadId
* messageId

Outlook:

* conversationId

Normalize both to:

thread_id (string)

---

# 🔎 REPLY DETECTOR WORKER

Every 15 minutes:

For each active sending_account:

* Fetch replies
* Match by thread_id
* Insert into messages
* Update outreach_logs
* Stop followups

Must handle:

* revoked tokens
* rate limits
* exponential backoff

---

# 📆 FOLLOWUP ENGINE

Daily job:

Find outreach_logs where:

reply_status = NO_REPLY
followup_status = PENDING
next_followup_due <= NOW()

Send reply in same thread.

Increment sequence_step.

---

# 🔐 ORG ISOLATION MIDDLEWARE

Every request:

* Validate JWT
* Inject org_id
* Filter queries automatically

Never allow cross-org reads.

---

# 💳 STRIPE

Implement:

* Create checkout session
* Webhook endpoint
* Verify signature
* Update subscription table
* Enforce monthly_limit before send

---

# 🧠 API CONTRACT (DEFINE ALL ENDPOINTS)

Must include:

Auth:

* POST /auth/login
* POST /auth/google
* POST /auth/microsoft

Campaigns:

* POST /campaigns
* GET /campaigns
* GET /campaigns/{id}
* PATCH /campaigns/{id}
* DELETE /campaigns/{id}

Sending Accounts:

* POST /sending-accounts/connect
* GET /sending-accounts
* PATCH /sending-accounts/{id}

Outreach:

* POST /outreach/send
* POST /outreach/bulk

Inbox:

* GET /inbox?campaign_id=&view=personal|shared
* GET /inbox/{conversation_id}

Billing:

* POST /billing/checkout
* POST /webhooks/stripe

Each endpoint must:

* Enforce role permissions
* Enforce org isolation
* Handle edge cases

---

# 🐳 DEPLOYMENT

Generate:

* Dockerfile
* docker-compose
* ENV template
* Production-ready settings

---

Perfect. We are now locking this into **real product mode**.

You want:

1. ✅ Backend must follow your existing **n8n workflow logic** (LeadGen + Outreach), but internalized — NOT webhook-driven.
2. ✅ A **separate FRONTEND MASTER PROMPT** to build a Success.ai-style UI with fully working button logic.
3. ✅ Everything production-ready.

Below is exactly what you asked for.

---

# 🧠 PART 1 — ADD THIS PATCH TO YOUR BACKEND MASTER FILE

Add this section to your `SAARTHI_BACKEND_MASTER_EXECUTION.md`

---

## 🔄 CRITICAL: INTERNALIZE N8N WORKFLOW LOGIC (NO WEBHOOK ARCHITECTURE)

Saarthi must replicate the existing n8n workflow logic from:

* LeadGen Latest.json
* email Latest.json

But this logic must be implemented as:

* Internal services
* Background workers
* Database-driven state machine
* NOT webhook-triggered pipelines

---

## 🏗 LEAD GENERATION PIPELINE (INTERNAL SERVICE)

### Replace n8n flow with:

LeadGenService

Flow:

1. Input:

   * industry
   * geography
   * company_size
   * keywords
   * campaign_id

2. Google Maps / SERP scraper service

3. Extract company domains

4. Email pattern generator

5. Email validation API call

6. AI Fit scoring (LLM optional)

7. Insert into leads table

8. Update lead status:

   * NEW
   * VALIDATED
   * REJECTED

This must run as:

* Async background task
* Or queue-based worker

No webhook calls allowed.

---

## 📧 OUTREACH PIPELINE (STATE MACHINE)

Replace n8n outreach logic with database-driven execution.

States:

Lead.status:

* NEW
* CONTACTED
* REPLIED
* BOUNCED
* STOPPED

Outreach logic:

1. Scheduler picks eligible leads
2. Rotation service selects sending account
3. Provider factory sends email
4. Capture:

   * thread_id
   * message_id
   * sent_at
5. Insert outreach_logs row (append-only)
6. Update lead status → CONTACTED

Followup logic:

* Daily cron
* Check next_followup_due
* Send reply in same thread
* Increment sequence_step
* Stop if reply detected

Reply detection:

* Poll provider
* Match thread_id
* Insert into messages
* Update:
  reply_status = REPLIED
  followup_status = STOPPED
  lead.status = REPLIED

This replaces n8n’s entire branching graph.

---

## 🧠 STATE-DRIVEN DESIGN RULE

No webhook chaining.
No external automation engines.

Everything must be:

* Event-driven
* DB-state-driven
* Transaction-safe

---

# 🚀 PART 2 — FRONTEND MASTER PROMPT (SUCCESS.AI STYLE)

Now here is your complete **copy-paste MD file** for Antigravity to build the frontend.

---

Save this as:

```
SAARTHI_FRONTEND_MASTER_EXECUTION.md
```

---

# 🎨 SAARTHI FRONTEND – FULL SUCCESS.AI STYLE EXECUTION

## ⚠️ READ CAREFULLY

You are building a production SaaS frontend.

Reference UI: app.success.ai

This is NOT static design.
Every button must function.
Every screen must connect to backend APIs.
State must be real.

Stack:

* Next.js (App Router)
* TypeScript
* TailwindCSS
* ShadCN UI
* React Query
* Zustand (minimal global state)

---

# 🧱 CORE UI STRUCTURE

## Layout

Sidebar (left):

* Dashboard
* Campaigns
* Leads
* Inbox
* Sending Accounts
* Billing
* Settings

Topbar:

* Organization switcher
* Personal/Shared Inbox toggle
* Profile dropdown

---

# 📊 DASHBOARD

Must show:

* Total leads
* Emails sent (month)
* Replies
* Reply rate
* Active campaigns
* Usage vs limit

All data fetched from:
GET /dashboard/summary

Charts:

* Emails sent per day
* Replies per day

---

# 📁 CAMPAIGNS MODULE

## Campaign List Page

GET /campaigns

Table:

* Name
* Status
* Leads count
* Emails sent
* Reply rate
* Actions: View / Edit / Pause

Button:

* Create Campaign

---

## Create Campaign Modal

Fields:

* Name
* Sequence steps (rich editor)
* Followup delay days
* Assign sending accounts (multi-select)

On submit:
POST /campaigns

---

## Campaign Detail Page

Tabs:

1. Overview
2. Leads
3. Sequence
4. Settings

---

# 👥 LEADS MODULE

GET /leads?campaign_id=

Table:

* Name
* Company
* Email
* Status
* Last contact
* Thread status

Actions:

* Add lead
* Bulk upload CSV
* Start outreach

Bulk upload:
POST /leads/bulk

---

# 📬 INBOX MODULE

Must look like Success.ai.

Left panel:
Conversation list

Right panel:
Thread messages

Filters:

* Campaign
* Personal / Shared
* Replied / Unreplied

APIs:
GET /inbox
GET /inbox/{conversation_id}

Reply box:
POST /inbox/reply

Must maintain thread_id.

---

# 📧 SENDING ACCOUNTS

GET /sending-accounts

Cards:

* Email
* Provider
* Daily limit
* Status
* Shared toggle

Buttons:

* Connect Gmail
* Connect Outlook

OAuth flow:
Redirect to backend endpoint.

After connect:
Show status ACTIVE.

---

# 💳 BILLING

GET /billing/status

Show:

* Plan
* Seats used
* Monthly limit
* Usage bar

Upgrade button:
POST /billing/checkout

---

# 🔐 AUTH

Pages:

* Login
* Signup
* Join Organization (invite token)
* Pending approval screen

Support:

* Email/password
* Google SSO
* Microsoft SSO

---

# 🧠 UI LOGIC REQUIREMENTS

1. All API calls via React Query.
2. All errors must show toast.
3. All mutations must invalidate queries.
4. All tables paginated.
5. Campaign filter applied globally.
6. Personal/shared toggle updates inbox query.
7. No mock data.

---

# 🎨 DESIGN SYSTEM RULES

* Clean white background
* Subtle borders
* Rounded-xl cards
* Soft shadow
* Blue primary accent
* Minimal gradients
* Dense data tables

---

# 🔁 GLOBAL STATE

Zustand only for:

* Auth token
* Selected campaign
* Inbox view mode

Everything else via React Query.

---

# 📦 DELIVERABLES

Generate:

* Full Next.js project
* Folder structure
* All pages
* All components
* API integration layer
* Auth handling
* Protected routes
* Layout system

No placeholders.
No TODOs.
No partial logic.

---

# 🚨 FINAL RULE

If backend endpoint is missing — STOP and request API contract.

We are building a real SaaS.

---

# 🎯 FINAL INSTRUCTION

Build this system carefully.

Do not simplify.

If any design decision conflicts with scalability, security, or multi-tenancy — STOP and ask.

If anything is unclear — ASK.

We are building a real SaaS.

---