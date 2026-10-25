# Technology for Consumer Rights Awareness
## Consumer Rights Awareness Portal — Community Engagement Project (CEP)

An educational, public-service web application designed to empower Indian consumers with statutory rights under the **Consumer Protection Act, 2019 (CPA 2019)**, documented grievance workflows, evidentiary checklists, and direct navigation to authentic government redressal services.

> **Educational Notice:** This portal is an educational and public information navigation system developed as a college Community Engagement Project. It is **NOT** a government agency, court of law, official complaint authority, or legal practice.

---

## 1. Project Objectives & Problem Statement

Millions of Indian citizens face consumer disputes—from delayed e-commerce refunds and warranty denials to hidden charges and failed UPI transactions. Many consumers are unaware that:
- Section 2(9) of the Consumer Protection Act, 2019 guarantees six enforceable consumer rights.
- Consumers can file and argue their own cases before District, State, and National Consumer Commissions without hiring an advocate.
- An informal, fast-track pre-litigation mechanism exists via the **National Consumer Helpline (NCH 1915)**.
- Formal legal complaints can be lodged electronically from home using **e-Daakhil** (`edaakhil.nic.in`).

This project bridges the gap by translating statutory provisions into accessible language and repeatable action steps.

---

## 2. Technology Stack

- **Backend:** Python 3, Flask 3.1, Jinja2 template engine
- **Database:** SQLite with foreign keys, constraints, and relational indexes
- **Frontend:** Semantic HTML5, Vanilla CSS Design System, Vanilla JavaScript (zero external CDN or node dependencies)
- **Seed Data:** Version-controlled, idempotent JSON datasets (`/data/*.json`)
- **Testing:** Automated test suite with `pytest`
- **Zero Paid/External APIs:** Completely self-contained and reproducible

---

## 3. Project Directory Structure

```text
CEP/
├── app.py                       # Flask application factory, routes, and JSON API handlers
├── config.py                    # Environment and app configuration classes
├── db.py                        # SQLite connection manager and query helpers
├── init_db.py                   # Idempotent database creation and seeder
├── requirements.txt             # Pinned, minimal Python dependencies
├── README.md                    # Project documentation and release guide
├── .env.example                 # Example configuration for local overrides and admin gating
├── .gitignore                   # Git exclusion rules
├── data/                        # Version-controlled statutory seed data
│   ├── sources.json             # Official government acts, gazettes, and portals
│   ├── rights.json              # 6 statutory rights under Section 2(9) CPA 2019
│   ├── issue_guides.json        # Step-by-step dispute procedures and evidence lists
│   ├── faqs.json                # Plain-language consumer questions and answers
│   └── quiz_questions.json      # Scenario-based consumer awareness quiz questions
├── instance/
│   └── consumer_rights.db       # Local SQLite database (created by init_db.py)
├── templates/                   # Jinja2 semantic HTML5 templates
│   ├── base.html                # Master layout with accessible navigation & footer
│   ├── index.html               # Home page with hero, search, categories & rights
│   ├── search.html              # Dedicated global search page with type & category filters
│   ├── wizard.html              # Interactive 4-step problem resolution guidance wizard
│   ├── rights.html              # Statutory Consumer Rights Library
│   ├── right_detail.html        # Individual statutory right detail view
│   ├── problems.html            # Common consumer problems catalog & filter
│   ├── guidance.html            # Dispute resolution overview & specific guides
│   ├── resources.html           # Official government services directory
│   ├── faqs.html                # Frequently asked questions with keyword filter & accordion
│   ├── quiz.html                # Interactive scenario quiz with server-side evaluation
│   ├── about.html               # Project overview, CEP methodology & objectives
│   ├── privacy.html             # Privacy ethics, data minimization & anonymous policy
│   ├── feedback.html            # Anonymous user feedback submission with PII detection
│   ├── admin_login.html         # Gated administrator login with security disclosure
│   ├── admin_sources.html       # Protected source provenance & link telemetry dashboard
│   ├── 404.html                 # Custom 404 error page (HTML / JSON)
│   └── 500.html                 # Custom 500 error page (HTML / JSON)
├── static/
│   ├── css/
│   │   └── style.css            # Editorial design system with CSS custom properties & print rules
│   ├── images/                  # Static image assets served by Flask (9 curated photos)
│   └── js/
│       ├── main.js              # Accessible mobile menu, live search & FAQ filtering
│       └── quiz.js              # Asynchronous quiz controller & score evaluation against API
├── scripts/
│   ├── audit_sources.py         # Relational database source & citation integrity audit
│   ├── check_source_links.py    # Official link reachability, latency & status monitor
│   ├── test_user_journeys.py    # Automated end-to-end user journeys (A through E) validator
│   └── verify_images.py         # Image assets integrity & HTTP 200 reachability validator
└── tests/
    ├── conftest.py              # Pytest fixtures and isolated test database
    └── test_app.py              # Comprehensive test suite (31 automated unit/integration tests)
```

---

## 4. Setup and Installation Instructions

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13 installed on your system.
- Zero external database services, cloud accounts, or paid API keys required.

### Step 1: Create and Activate Virtual Environment
On Windows (PowerShell / Command Prompt):
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

On Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Pinned Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Initialize and Seed the Database
Run the idempotent initialisation script:
```bash
python init_db.py
```
*Note: This command can be executed multiple times safely. It updates content from JSON seed files without creating duplicates, never erases existing user feedback, and maintains relational integrity.*

### Step 4: Run the Application
```bash
python app.py
```
Open your browser and navigate to:
```text
http://127.0.0.1:5000/
```

---

## 5. Running Automated Tests

Run the complete test suite with `pytest`:
```bash
pytest -v

# Run the live end-to-end user journeys (A through E) validator:
python scripts/test_user_journeys.py
```

All 31 unit and integration tests verify:
- Home page and core editorial headings
- Rights catalog, detail pages, and backward-compatible redirects (`/rights/right-to-information`)
- Common problems directory and category filtering
- Multi-step guided problem resolution wizard (`/wizard`)
- Global search page with type scoping, empty states, and input truncation (`/search`)
- Search security against SQL injection (`' OR 1=1 --`) and XSS payload escaping
- Step-by-step guidance roadmaps and 3-tier interactive evidence checklists
- Official government services directory
- FAQ accordion and in-page keyword search
- Server-side quiz scoring calculation, percentage evaluation, and itemized legal explanations
- Anonymous feedback submission, length enforcement, and automated PII filtering (Aadhaar, card, phone numbers)
- Administrative authentication gating when unconfigured vs. configured
- Administrative review dashboard and audit log recording (`source_audit_logs`)
- JSON API endpoints (`/api/search`, `/api/guides`, `/api/guides/<slug>`, `/api/resources`, `/api/quiz/submit`, `/api/feedback`)
- Custom error handlers (HTML for web navigation, JSON for API requests)
- Database relational integrity, zero duplicate slugs, and zero missing source citations
- Static CSS and JavaScript asset availability

---

## 6. Official Data-Source Policy & Provenance Rules

### Non-Negotiable Content-Integrity Rule
This portal **never invents** consumer rights, statutory provisions, complaint procedures, document requirements, pecuniary thresholds, filing fees, limitation periods, helpline numbers, or complaint outcomes.

- **Primary Source Mandate:** All factual and legal claims originate from primary official government sources:
  - Ministry of Law and Justice / Department of Consumer Affairs (DoCA)
  - National Consumer Helpline (NCH / INGRAM)
  - e-Jagriti Unified Redressal Portal (DoCA / NIC)
  - Bureau of Indian Standards (BIS) & BIS Care
  - Reserve Bank of India (RBI)
  - Central Consumer Protection Authority (CCPA)
  - Legal Metrology Division, Government of India
  - India Code Legislative Repository
- **Academic Papers Exception:** Research papers may inform design, usability, and UI architecture, but are **never** treated as legal authority.
- **AI Hallucination Prohibition:** Generative AI is strictly restricted to development assistance. Substantive legal claims must be grounded directly in verified source records.

### Verification States
Every source record in the Source Registry (`sources.json`) and database table maintains an explicit verification state:
1. `verified`: Canonical official page inspected; text, provisions, and URLs confirmed accurate.
2. `pending_verification`: Source noted or operational, but specific procedure/regulation awaiting manual web verification. Substantive legal assertions are withheld from verified guidance.
3. `needs_review`: Previously verified source where government rules, gazettes, or URLs have changed or require re-evaluation.
4. `unavailable`: Official portal or gazette page is temporarily offline or archived.

---

## 7. Content Provenance & Audit Tooling

### Running the Source Audit Report
Run the built-in provenance audit script to verify relational integrity, ensure 100% citation coverage, and detect unverified claims:
```bash
python scripts/audit_sources.py
```
The audit report outputs:
- Total source records indexed (11 records: 10 verified, 1 pending verification)
- Verified vs. unverified sources
- Published vs. unpublished guides (9 published: 8 verified, 1 pending verification)
- Content entries missing source citations (0 across rights, guides, and FAQs)
- Sources flagged for review (0 flagged)

### Testing Official Source Link Latency & Reachability
To check reachability and response latencies of all canonical government URLs:
```bash
python scripts/check_source_links.py --test
# Or test all sources with a 5-second timeout:
python scripts/check_source_links.py --timeout 5
```
Results and HTTP response codes are logged directly into the `source_checks` table in SQLite. Link availability is strictly isolated from content verification.

### Inspecting the Public Source Registry
Visit `http://127.0.0.1:5000/sources` to explore the public Source Registry & Audit Dashboard, featuring:
- Live metric cards (Total sources, verified sources, pending verification, citation integrity)
- Editorial provenance standards
- Full directory of official sources with canonical links, responsible authorities, and verified provisions supported.

---

## 8. Procedure for Adding or Reviewing Content

To maintain academic integrity and statutory accuracy, follow this 4-step workflow when contributing content:

1. **Primary Source Research:**
   - Locate the official gazette notification, act on *India Code*, or portal page on a `.gov.in` / `.nic.in` domain.
   - Record canonical URL, responsible ministry/authority, publication date, and exact section or rule number.
2. **Register in `data/sources.json`:**
   - Add a source record with unique code, canonical URL, domain, organisation, verification status (`verified` or `pending_verification`), genuine `last_verified_at` date, and bulleted `verified_claims_or_topics`.
3. **Map to Content Seeds (`rights.json`, `issue_guides.json`, `faqs.json`):**
   - Reference the exact `source_code`.
   - Separate evidence checklists into three distinct tiers:
     - `officially_specified_documents` (mandatory filings for e-Jagriti)
     - `useful_to_preserve` (recommended supporting evidence)
     - `conditional_documents` (situation-dependent proof)
   - Include realistic statutory caveats and escalation boundaries (no guarantees of refunds or favorable outcomes).
4. **Execute Database Sync & Audit:**
   ```bash
   python init_db.py
   python scripts/audit_sources.py
   pytest -v
   ```

---

## 9. Core Routes & Endpoints

| Route | Method | Description |
|---|---|---|
| `/` | GET | Home page: Hero, live autocomplete search, categories, rights preview |
| `/search` | GET | Global verified search page with content type & category filtering (`?q=...`) |
| `/wizard` | GET | Interactive 4-step consumer problem resolution guidance wizard |
| `/rights` | GET | Consumer Rights Library (the 6 rights under Section 2(9) CPA 2019) |
| `/rights/<slug>` | GET | Individual statutory right details, plain-language meaning, scenarios & source citation |
| `/problems` | GET | Common consumer problems directory with category filters |
| `/guidance` | GET | Interactive guidance entry point & problem selector |
| `/guidance/<slug>` | GET | Step-by-Step dispute resolution roadmap, 3-tier evidence checklist & caveats |
| `/resources` | GET | Official directory: What services handle vs. what they do NOT do |
| `/sources` | GET | Public Source Registry & Verification Audit dashboard |
| `/faqs` | GET | Frequently asked questions with verified source badges, keyword search & pecuniary limits |
| `/quiz` | GET, POST | Consumer awareness assessment quiz with server-side score tracking |
| `/about` | GET | Academic overview, CEP objectives, and methodology |
| `/privacy` | GET | Data ethics, zero cookies, and privacy statement |
| `/feedback` | GET, POST | Anonymous user feedback collection with PII protection filter |
| `/admin/login` | GET, POST | Protected administrator login (gated when credentials unconfigured) |
| `/admin/logout` | POST | Administrator session termination |
| `/admin/sources` | GET | Protected source review dashboard with link telemetry and audit trail |
| `/admin/sources/update`| POST | Safe update to source verification metadata with mandatory audit note |
| `/api/search` | GET | JSON search endpoint across rights, guides, FAQs, and resources (`?q=...`) |
| `/api/guides` | GET | Published guidance records in JSON format with structured checklists |
| `/api/guides/<slug>` | GET | Single published guide record in JSON format |
| `/api/resources` | GET | Official dispute resolution and regulatory services in JSON format |
| `/api/quiz/submit` | POST | Stateless backend quiz answer evaluation and scoring |
| `/api/feedback` | POST | Anonymous feedback submission with backend input validation |

---

## 10. Academic Project Context

- **Course:** College Community Engagement Project (CEP)
- **Project Title:** Technology for Consumer Rights Awareness
- **Target Audience:** Indian consumers, students, retail buyers, and digital marketplace shoppers
- **Delivery Status:** Complete implementation of all foundation, content provenance, interactive features, responsive accessibility, and security controls across 31 verified automated tests.

