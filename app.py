from functools import wraps
import hmac
import json
import os
import re
from datetime import datetime
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    flash,
    redirect,
    url_for,
    abort,
    session,
    g,
)
from config import config_by_name
import db

def create_app(config_name=None):
    """Application factory for the Consumer Rights Awareness Portal."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Initialize database teardown
    db.init_app(app)

    # Register custom Jinja template filters
    @app.template_filter("from_json")
    def from_json_filter(value):
        if not value:
            return []
        if isinstance(value, (list, dict)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return []

    # Context processor for global template variables
    @app.context_processor
    def inject_global_data():
        admin_user = app.config.get("ADMIN_USERNAME")
        admin_pass = app.config.get("ADMIN_PASSWORD")
        return {
            "portal_name": app.config.get("PORTAL_NAME", "Consumer Rights Awareness Portal"),
            "project_title": app.config.get("PROJECT_TITLE", "Technology for Consumer Rights Awareness"),
            "current_year": 2026,
            "helpline_number": "1915",
            "active_endpoint": request.endpoint or "",
            "is_admin": session.get("is_admin", False),
            "admin_configured": bool(admin_user and admin_pass),
        }

    def admin_required(f):
        """Decorator to gate admin-only routes."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("is_admin"):
                flash("Administrator authentication is required to access the review dashboard.", "error")
                return redirect(url_for("admin_login"))
            return f(*args, **kwargs)
        return decorated_function

    # -------------------------------------------------------------
    # SEARCH HELPER
    # -------------------------------------------------------------

    def search_content(database, raw_query, type_filter="all", category_filter=None, limit=50):
        """
        Execute parameterized search across rights, guides, faqs, and official resources.
        Returns curated, source-grounded results without hallucinating unverified claims.
        """
        query = (raw_query or "").strip()
        if not query:
            return []

        # Enforce reasonable input length limit (100 characters max)
        if len(query) > 100:
            query = query[:100]

        pattern = f"%{query}%"
        results = []

        # 1. Search Consumer Rights
        if type_filter in ("all", "right"):
            rights_sql = """
            SELECT r.slug, r.title, r.summary, r.legal_name, r.statutory_provision,
                   r.verification_status, s.name as source_name
            FROM rights r
            JOIN sources s ON r.source_id = s.id
            WHERE r.title LIKE ? OR r.summary LIKE ? OR r.legal_name LIKE ?
               OR r.practical_application LIKE ? OR r.plain_language_explanation LIKE ?
               OR r.statutory_provision LIKE ?
            """
            rows = database.execute(rights_sql, (pattern, pattern, pattern, pattern, pattern, pattern)).fetchall()
            for row in rows:
                results.append({
                    "type": "right",
                    "type_label": "Statutory Right",
                    "slug": row["slug"],
                    "title": row["title"],
                    "summary": row["summary"],
                    "detail": row["statutory_provision"],
                    "category": "Statutory Consumer Rights",
                    "url": f"/rights/{row['slug']}",
                    "source_name": row["source_name"],
                    "verification_status": row["verification_status"],
                })

        # 2. Search Issue Guides
        if type_filter in ("all", "guide"):
            guides_sql = """
            SELECT g.slug, g.title, g.summary, g.category, g.problem_statement,
                   g.typical_situation, g.verification_status, s.name as source_name
            FROM issue_guides g
            JOIN sources s ON g.source_id = s.id
            WHERE g.is_published = 1 AND (
                g.title LIKE ? OR g.summary LIKE ? OR g.problem_statement LIKE ?
                OR g.typical_situation LIKE ? OR g.category LIKE ?
            )
            """
            params = [pattern, pattern, pattern, pattern, pattern]
            if category_filter:
                guides_sql += " AND g.category = ?"
                params.append(category_filter)

            rows = database.execute(guides_sql, params).fetchall()
            for row in rows:
                results.append({
                    "type": "guide",
                    "type_label": "Resolution Guide",
                    "slug": row["slug"],
                    "title": row["title"],
                    "summary": row["summary"],
                    "detail": row["category"],
                    "category": row["category"],
                    "url": f"/guidance/{row['slug']}",
                    "source_name": row["source_name"],
                    "verification_status": row["verification_status"],
                })

        # 3. Search FAQs
        if type_filter in ("all", "faq"):
            faqs_sql = """
            SELECT f.id, f.question, f.answer, f.category, f.verification_status,
                   s.name as source_name
            FROM faqs f
            LEFT JOIN sources s ON f.source_id = s.id
            WHERE f.question LIKE ? OR f.answer LIKE ? OR f.category LIKE ?
            """
            params = [pattern, pattern, pattern]
            if category_filter:
                faqs_sql += " AND f.category = ?"
                params.append(category_filter)

            rows = database.execute(faqs_sql, params).fetchall()
            for row in rows:
                summary_text = row["answer"][:180] + "..." if len(row["answer"]) > 180 else row["answer"]
                results.append({
                    "type": "faq",
                    "type_label": "FAQ",
                    "slug": f"faq-{row['id']}",
                    "title": row["question"],
                    "summary": summary_text,
                    "detail": row["category"],
                    "category": row["category"],
                    "url": f"/faqs#faq-q-{row['id']}",
                    "source_name": row["source_name"] or "Statutory Source",
                    "verification_status": row["verification_status"] or "verified",
                })

        # 4. Search Official Resources
        if type_filter in ("all", "resource"):
            resources_sql = """
            SELECT s.id, s.code, s.name, s.organisation, s.authority, s.url,
                   s.topic, s.summary, s.source_type, s.verification_status
            FROM sources s
            WHERE s.name LIKE ? OR s.organisation LIKE ? OR s.authority LIKE ?
               OR s.topic LIKE ? OR s.summary LIKE ? OR s.domain LIKE ?
            """
            rows = database.execute(resources_sql, (pattern, pattern, pattern, pattern, pattern, pattern)).fetchall()
            for row in rows:
                summary_text = (row["summary"] or "")[:180] + "..." if len(row["summary"] or "") > 180 else (row["summary"] or "")
                results.append({
                    "type": "resource",
                    "type_label": "Official Service",
                    "slug": row["code"].lower(),
                    "title": row["name"],
                    "summary": summary_text,
                    "detail": row["organisation"],
                    "category": "Official Dispute Authorities",
                    "url": f"/resources#service-{row['code'].lower()}",
                    "source_name": row["authority"],
                    "verification_status": row["verification_status"],
                })

        return results[:limit]

    # -------------------------------------------------------------
    # WIZARD DOMAINS SPECIFICATION
    # -------------------------------------------------------------

    WIZARD_DOMAINS = [
        {
            "id": "ecommerce",
            "category": "Online Shopping & E-Commerce",
            "title": "Online Shopping, Marketplaces & Deliveries",
            "description": "Orders placed on e-commerce websites, mobile apps, or online marketplaces.",
            "icon": "shopping-bag",
            "question": "What specific problem did you experience with the seller or platform?",
            "options": [
                {
                    "id": "opt_refund",
                    "label": "Delayed Refund or Return Rejection",
                    "desc": "I cancelled an order or returned a package, but the merchant stalled or rejected my refund beyond committed time limits.",
                    "slug": "e-commerce-refund-delays",
                },
                {
                    "id": "opt_wrong",
                    "label": "Wrong or Mismatched Product Delivered",
                    "desc": "The parcel contained a completely different item, incorrect size, wrong model, or empty package.",
                    "slug": "wrong-product-delivered",
                },
                {
                    "id": "opt_dark",
                    "label": "Dark Patterns or Deceptive Checkout Charges",
                    "desc": "The app tricked me with pre-ticked add-on fees, hidden delivery surcharges, subscription traps, or false countdown timers.",
                    "slug": "online-shopping-dark-patterns",
                },
                {
                    "id": "opt_unsupported_ecomm",
                    "label": "Another e-commerce dispute (e.g. account blocking, seller fraud)",
                    "desc": "My issue is not covered above.",
                    "slug": None,
                }
            ]
        },
        {
            "id": "product_quality",
            "category": "Product Quality & Safety",
            "title": "Defective Goods, Warranty & Certification",
            "description": "Physical merchandise, electronics, household appliances, ISI marks, and hallmarking.",
            "icon": "shield-check",
            "question": "What is the nature of the product defect or quality concern?",
            "options": [
                {
                    "id": "opt_warranty",
                    "label": "Defective Item or Warranty Repair Refusal",
                    "desc": "The appliance or gadget developed a manufacturing fault and the company or service center refuses warranty repair.",
                    "slug": "defective-goods-warranty",
                },
                {
                    "id": "opt_certification",
                    "label": "Counterfeit ISI Mark or Missing Gold Hallmarking",
                    "desc": "Suspected fake certification mark on mandatory safety goods, or gold jewelry sold without a 6-digit HUID hallmark.",
                    "slug": "product-certification-hallmark",
                },
                {
                    "id": "opt_unsupported_quality",
                    "label": "Another product issue not listed above",
                    "desc": "My issue is not covered here.",
                    "slug": None,
                }
            ]
        },
        {
            "id": "pricing",
            "category": "Pricing & Fair Trade Practices",
            "title": "Overcharging, MRP & Extra Surcharges",
            "description": "Retail billing, price discrepancies, cooling charges, and dual MRP pricing.",
            "icon": "tag",
            "question": "How did the overcharging occur?",
            "options": [
                {
                    "id": "opt_mrp",
                    "label": "Charged More Than Maximum Retail Price (MRP)",
                    "desc": "Shopkeeper or vendor charged above the printed MRP, or added extra fees for refrigeration/cooling chilled drinks.",
                    "slug": "overcharging-above-mrp",
                },
                {
                    "id": "opt_unsupported_pricing",
                    "label": "Another billing or pricing practice",
                    "desc": "Different overcharging or billing scenario.",
                    "slug": None,
                }
            ]
        },
        {
            "id": "payments",
            "category": "Banking & Digital Payments",
            "title": "Failed UPI, Card Debits & Payment Glitches",
            "description": "Electronic payments, failed transfers, QR code debits, and delayed auto-reversals.",
            "icon": "credit-card",
            "question": "What occurred during the electronic transaction?",
            "options": [
                {
                    "id": "opt_upi",
                    "label": "Account Debited but Merchant Not Paid (Failed UPI/Card)",
                    "desc": "Money left my bank account but transaction timed out or failed, and reversal was delayed beyond the RBI T+1 deadline.",
                    "slug": "digital-payment-failures",
                },
                {
                    "id": "opt_unsupported_banking",
                    "label": "Another banking dispute (unauthorized fraud, loan charges)",
                    "desc": "Dispute involving unauthorized transactions or loan issues.",
                    "slug": None,
                }
            ]
        },
        {
            "id": "advertising",
            "category": "Advertising Standards & Consumer Choice",
            "title": "Misleading Ads & False Promotional Claims",
            "description": "Deceptive advertisements, exaggerated health/efficacy claims, and false endorsements.",
            "icon": "alert-circle",
            "question": "What is misleading about the advertisement?",
            "options": [
                {
                    "id": "opt_ads",
                    "label": "Exaggerated Claims, False Guarantees, or Fake Endorsements",
                    "desc": "The product does not perform as advertised, or celebrity endorsement makes unverified statutory claims.",
                    "slug": "misleading-advertisements",
                },
                {
                    "id": "opt_unsupported_ads",
                    "label": "Another advertising grievance",
                    "desc": "Different advertising complaint.",
                    "slug": None,
                }
            ]
        },
        {
            "id": "telecom",
            "category": "Essential Services & Telecommunications",
            "title": "Mobile, Broadband & Telecommunications",
            "description": "Telecom service deficiency, billing discrepancies, and call drop issues (Pending Verification).",
            "icon": "phone",
            "question": "What issue are you facing with your telecom service provider?",
            "options": [
                {
                    "id": "opt_telecom",
                    "label": "Billing Discrepancy or Unsolicited Commercial Calls",
                    "desc": "Operator charged unauthorized service fees, failed to resolve complaints, or violated DND preferences.",
                    "slug": "service-deficiency-telecom",
                },
                {
                    "id": "opt_unsupported_telecom",
                    "label": "Another telecom or utility issue",
                    "desc": "Another service dispute.",
                    "slug": None,
                }
            ]
        }
    ]

    # -------------------------------------------------------------
    # HEALTH CHECK (Render & Uptime Monitoring)
    # -------------------------------------------------------------

    @app.route("/healthz")
    def healthz():
        """
        Production health check endpoint for Render and uptime monitoring.
        Verifies application liveness and database connectivity safely without exposing internal details.
        """
        try:
            database = db.get_db()
            database.execute("SELECT 1").fetchone()
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "portal": app.config.get("PORTAL_NAME", "Consumer Rights Awareness Portal")
            }), 200
        except Exception:
            return jsonify({
                "status": "degraded",
                "database": "disconnected"
            }), 503

    # -------------------------------------------------------------
    # CORE ROUTES
    # -------------------------------------------------------------

    @app.route("/")
    def index():
        """Home page with hero message, search, categories, rights preview and resources."""
        database = db.get_db()
        rights = database.execute(
            "SELECT r.*, s.name as source_name, s.code as source_code FROM rights r JOIN sources s ON r.source_id = s.id ORDER BY r.id"
        ).fetchall()
        
        guides = database.execute(
            "SELECT g.*, s.name as source_name FROM issue_guides g JOIN sources s ON g.source_id = s.id WHERE g.is_published = 1 ORDER BY g.id LIMIT 4"
        ).fetchall()

        categories = database.execute(
            "SELECT DISTINCT category, COUNT(*) as guide_count FROM issue_guides WHERE is_published = 1 GROUP BY category"
        ).fetchall()

        faqs = database.execute(
            "SELECT * FROM faqs ORDER BY sort_order LIMIT 4"
        ).fetchall()

        return render_template(
            "index.html",
            rights=rights,
            guides=guides,
            categories=categories,
            faqs=faqs,
        )

    @app.route("/search")
    def search_page():
        """Dedicated global search page with filters and content-type scoping."""
        database = db.get_db()
        query = request.args.get("q", "").strip()[:100]
        type_filter = request.args.get("type", "all").strip().lower()
        if type_filter not in ("all", "right", "guide", "faq", "resource"):
            type_filter = "all"
        category_filter = request.args.get("category", "").strip()

        results = []
        if query:
            results = search_content(
                database=database,
                raw_query=query,
                type_filter=type_filter,
                category_filter=category_filter or None,
            )

        categories_rows = database.execute(
            "SELECT DISTINCT category FROM issue_guides WHERE is_published = 1 ORDER BY category"
        ).fetchall()
        categories = [c["category"] for c in categories_rows]

        return render_template(
            "search.html",
            query=query,
            type_filter=type_filter,
            category_filter=category_filter,
            results=results,
            count=len(results),
            categories=categories,
        )

    @app.route("/rights")
    def rights_list():
        """Consumer rights library listing all statutory rights under CPA 2019 with search and filters."""
        database = db.get_db()
        query = request.args.get("q", "").strip()
        provision_filter = request.args.get("provision", "").strip()

        sql = """
        SELECT r.*, s.name as source_name, s.code as source_code, s.authority as source_authority, s.url as source_url
        FROM rights r
        JOIN sources s ON r.source_id = s.id
        WHERE 1=1
        """
        params = []
        if query:
            pattern = f"%{query}%"
            sql += " AND (r.title LIKE ? OR r.summary LIKE ? OR r.legal_name LIKE ? OR r.statutory_provision LIKE ?)"
            params.extend([pattern, pattern, pattern, pattern])
        if provision_filter:
            sql += " AND r.statutory_provision = ?"
            params.append(provision_filter)

        sql += " ORDER BY r.id"
        rights = database.execute(sql, params).fetchall()

        provisions = database.execute("SELECT DISTINCT statutory_provision FROM rights ORDER BY id").fetchall()

        return render_template(
            "rights.html",
            rights=rights,
            query=query,
            provision_filter=provision_filter,
            provisions=[p["statutory_provision"] for p in provisions],
        )

    @app.route("/rights/<slug>")
    def right_detail(slug):
        """Individual statutory right detail view with full statutory reference and protections."""
        # Handle backward-compatible aliases
        if slug in ("right-to-information", "information"):
            return redirect(url_for("right_detail", slug="right-to-be-informed"))
        if slug in ("right-to-redressal", "redressal"):
            return redirect(url_for("right_detail", slug="right-to-seek-redressal"))

        database = db.get_db()
        right = database.execute(
            """
            SELECT r.*, s.name as source_name, s.code as source_code, s.organisation as source_org,
                   s.authority as source_authority, s.url as source_url, s.legal_reference as source_legal_ref,
                   s.verification_status as source_v_status, s.last_verified_at as source_v_date
            FROM rights r
            JOIN sources s ON r.source_id = s.id
            WHERE r.slug = ?
            """,
            (slug,),
        ).fetchone()

        if not right:
            abort(404)

        # Related guides that cite this right
        pattern = f"%{slug}%"
        related_guides = database.execute(
            "SELECT * FROM issue_guides WHERE relevant_legal_rights LIKE ? AND is_published = 1",
            (pattern,),
        ).fetchall()

        # Other rights for quick navigation
        other_rights = database.execute(
            "SELECT slug, title FROM rights WHERE slug != ? ORDER BY id",
            (slug,),
        ).fetchall()

        return render_template(
            "right_detail.html",
            right=right,
            related_guides=related_guides,
            other_rights=other_rights,
        )

    @app.route("/problems")
    def problems():
        """Common consumer problems directory with categorization and search."""
        database = db.get_db()
        category_filter = request.args.get("category", "").strip()

        if category_filter:
            guides = database.execute(
                """
                SELECT g.*, s.name as source_name, s.authority as source_authority
                FROM issue_guides g
                JOIN sources s ON g.source_id = s.id
                WHERE g.is_published = 1 AND g.category = ?
                ORDER BY g.title
                """,
                (category_filter,),
            ).fetchall()
        else:
            guides = database.execute(
                """
                SELECT g.*, s.name as source_name, s.authority as source_authority
                FROM issue_guides g
                JOIN sources s ON g.source_id = s.id
                WHERE g.is_published = 1
                ORDER BY g.category, g.title
                """
            ).fetchall()

        categories = database.execute(
            "SELECT category, COUNT(*) as guide_count FROM issue_guides WHERE is_published = 1 GROUP BY category ORDER BY category"
        ).fetchall()

        return render_template(
            "problems.html",
            guides=guides,
            categories=categories,
            selected_category=category_filter,
        )

    @app.route("/guidance")
    @app.route("/guidance/<slug>")
    def guidance(slug=None):
        """Interactive guidance entry point or problem-specific resolution walkthrough."""
        database = db.get_db()

        if slug:
            guide = database.execute(
                """
                SELECT g.*, s.name as source_name, s.code as source_code, s.organisation as source_org,
                       s.authority as source_authority, s.url as source_url, s.legal_reference as source_legal_ref,
                       s.verification_status as source_v_status, s.last_verified_at as source_v_date
                FROM issue_guides g
                JOIN sources s ON g.source_id = s.id
                WHERE g.slug = ? AND g.is_published = 1
                """,
                (slug,),
            ).fetchone()

            if not guide:
                abort(404)

            # Retrieve details of the associated legal rights
            rights_slugs = json.loads(guide["relevant_legal_rights"]) if guide["relevant_legal_rights"] else []
            associated_rights = []
            if rights_slugs:
                placeholders = ",".join("?" for _ in rights_slugs)
                associated_rights = database.execute(
                    f"SELECT slug, title, legal_name, statutory_provision FROM rights WHERE slug IN ({placeholders})",
                    rights_slugs,
                ).fetchall()

            # Parse structured evidence checklist
            checklist = {}
            if guide["evidence_checklist"]:
                try:
                    checklist = json.loads(guide["evidence_checklist"])
                except Exception:
                    pass

            # All published guides for sidebar navigation
            other_guides = database.execute(
                "SELECT slug, title, category FROM issue_guides WHERE slug != ? AND is_published = 1 ORDER BY category, title",
                (slug,),
            ).fetchall()

            return render_template(
                "guidance.html",
                guide=guide,
                checklist=checklist,
                associated_rights=associated_rights,
                other_guides=other_guides,
                is_detail=True,
            )

        # Overview / interactive guided selector
        all_guides = database.execute(
            """
            SELECT g.*, s.name as source_name
            FROM issue_guides g
            JOIN sources s ON g.source_id = s.id
            WHERE g.is_published = 1
            ORDER BY g.category, g.title
            """
        ).fetchall()

        categories = database.execute(
            "SELECT DISTINCT category FROM issue_guides WHERE is_published = 1 ORDER BY category"
        ).fetchall()

        return render_template(
            "guidance.html",
            guides=all_guides,
            categories=[c["category"] for c in categories],
            is_detail=False,
        )

    @app.route("/wizard")
    def wizard():
        """Interactive multi-step consumer problem guidance wizard."""
        database = db.get_db()
        domain_id = request.args.get("domain", "").strip()
        guide_slug = request.args.get("guide", "").strip()
        unsupported = request.args.get("unsupported", "").strip() == "true"

        # Check if matched to a specific verified guide
        if guide_slug:
            guide = database.execute(
                """
                SELECT g.*, s.name as source_name, s.code as source_code, s.organisation as source_org,
                       s.authority as source_authority, s.url as source_url, s.legal_reference as source_legal_ref,
                       s.verification_status as source_v_status, s.last_verified_at as source_v_date
                FROM issue_guides g
                JOIN sources s ON g.source_id = s.id
                WHERE g.slug = ? AND g.is_published = 1
                """,
                (guide_slug,),
            ).fetchone()

            if guide:
                rights_slugs = json.loads(guide["relevant_legal_rights"]) if guide["relevant_legal_rights"] else []
                associated_rights = []
                if rights_slugs:
                    placeholders = ",".join("?" for _ in rights_slugs)
                    associated_rights = database.execute(
                        f"SELECT slug, title, legal_name, statutory_provision FROM rights WHERE slug IN ({placeholders})",
                        rights_slugs,
                    ).fetchall()

                checklist = {}
                if guide["evidence_checklist"]:
                    try:
                        checklist = json.loads(guide["evidence_checklist"])
                    except Exception:
                        pass

                return render_template(
                    "wizard.html",
                    step=3,
                    guide=guide,
                    checklist=checklist,
                    associated_rights=associated_rights,
                    domains=WIZARD_DOMAINS,
                    selected_domain=None,
                )

        # Check if user selected an unsupported sector
        if unsupported:
            return render_template(
                "wizard.html",
                step="unsupported",
                domains=WIZARD_DOMAINS,
                selected_domain=None,
            )

        # Step 2: User picked a domain, show follow-up question
        selected_domain = None
        if domain_id:
            for d in WIZARD_DOMAINS:
                if d["id"] == domain_id:
                    selected_domain = d
                    break

        if selected_domain:
            return render_template(
                "wizard.html",
                step=2,
                selected_domain=selected_domain,
                domains=WIZARD_DOMAINS,
            )

        # Step 1: Default domain selector
        return render_template(
            "wizard.html",
            step=1,
            domains=WIZARD_DOMAINS,
            selected_domain=None,
        )

    @app.route("/resources")
    def resources():
        """Official service directory with authoritative dispute portals and helplines."""
        database = db.get_db()
        category_filter = request.args.get("category", "").strip()
        query = request.args.get("q", "").strip()

        sql = """
        SELECT s.*, 
               (SELECT COUNT(*) FROM rights WHERE source_id = s.id) as rights_count,
               (SELECT COUNT(*) FROM issue_guides WHERE source_id = s.id) as guides_count
        FROM sources s
        WHERE 1=1
        """
        params = []
        if category_filter:
            sql += " AND s.source_type = ?"
            params.append(category_filter)
        if query:
            pattern = f"%{query}%"
            sql += " AND (s.name LIKE ? OR s.organisation LIKE ? OR s.topic LIKE ? OR s.summary LIKE ?)"
            params.extend([pattern, pattern, pattern, pattern])

        sql += " ORDER BY s.id"
        sources = database.execute(sql, params).fetchall()

        categories_rows = database.execute("SELECT DISTINCT source_type FROM sources ORDER BY source_type").fetchall()
        categories = [c["source_type"] for c in categories_rows]

        return render_template(
            "resources.html",
            sources=sources,
            categories=categories,
            selected_category=category_filter,
            query=query,
        )

    @app.route("/sources")
    def sources_registry():
        """Public Source Registry & Verification Audit page."""
        database = db.get_db()
        sources = database.execute(
            """
            SELECT s.*,
                   (SELECT COUNT(*) FROM rights WHERE source_id = s.id) as rights_count,
                   (SELECT COUNT(*) FROM issue_guides WHERE source_id = s.id) as guides_count,
                   (SELECT COUNT(*) FROM faqs WHERE source_id = s.id) as faqs_count
            FROM sources s
            ORDER BY s.id
            """
        ).fetchall()

        counts = {
            "total_sources": len(sources),
            "verified_sources": sum(1 for s in sources if s["verification_status"] == "verified"),
            "pending_sources": sum(1 for s in sources if s["verification_status"] == "pending_verification"),
            "needs_review_sources": sum(1 for s in sources if s["verification_status"] == "needs_review"),
            "published_guides": database.execute("SELECT COUNT(*) as c FROM issue_guides WHERE is_published = 1").fetchone()["c"],
            "unpublished_guides": database.execute("SELECT COUNT(*) as c FROM issue_guides WHERE is_published = 0").fetchone()["c"],
            "missing_citations": database.execute(
                "SELECT (SELECT COUNT(*) FROM rights WHERE source_id IS NULL) + "
                "(SELECT COUNT(*) FROM issue_guides WHERE source_id IS NULL) + "
                "(SELECT COUNT(*) FROM faqs WHERE source_id IS NULL) as c"
            ).fetchone()["c"],
            "total_rights": database.execute("SELECT COUNT(*) as c FROM rights").fetchone()["c"],
            "total_guides": database.execute("SELECT COUNT(*) as c FROM issue_guides WHERE is_published = 1").fetchone()["c"],
            "total_faqs": database.execute("SELECT COUNT(*) as c FROM faqs").fetchone()["c"],
        }

        return render_template("sources.html", sources=sources, counts=counts)

    @app.route("/faqs")
    def faqs():
        """Frequently asked questions organized by category with source references and search."""
        database = db.get_db()
        category_filter = request.args.get("category", "").strip()
        query = request.args.get("q", "").strip()

        sql = """
        SELECT f.*, s.name as source_name, s.code as source_code, s.url as source_url, s.organisation as source_org
        FROM faqs f
        LEFT JOIN sources s ON f.source_id = s.id
        WHERE 1=1
        """
        params = []
        if category_filter:
            sql += " AND f.category = ?"
            params.append(category_filter)
        if query:
            pattern = f"%{query}%"
            sql += " AND (f.question LIKE ? OR f.answer LIKE ?)"
            params.extend([pattern, pattern])

        sql += " ORDER BY f.category, f.sort_order"
        faqs_rows = database.execute(sql, params).fetchall()

        categories = database.execute(
            "SELECT DISTINCT category FROM faqs ORDER BY category"
        ).fetchall()

        return render_template(
            "faqs.html",
            faqs=faqs_rows,
            categories=[c["category"] for c in categories],
            selected_category=category_filter,
            query=query,
        )

    @app.route("/quiz", methods=["GET", "POST"])
    def quiz():
        """Consumer-awareness interactive quiz with explanations and backend score tracking."""
        database = db.get_db()
        questions = database.execute(
            """
            SELECT q.*, s.name as source_name, s.code as source_code
            FROM quiz_questions q
            LEFT JOIN sources s ON q.source_id = s.id
            ORDER BY q.id
            """
        ).fetchall()

        results = None
        user_answers = {}

        if request.method == "POST":
            # Server-side score calculation
            score = 0
            breakdown = []
            for q in questions:
                qid = str(q["id"])
                user_val = request.form.get(f"question_{qid}", "").strip().upper()
                user_answers[qid] = user_val
                correct_val = q["correct_option"].strip().upper()
                is_correct = (user_val == correct_val)
                if is_correct:
                    score += 1
                breakdown.append({
                    "id": q["id"],
                    "question": q["question"],
                    "user_answer": user_val,
                    "correct_option": correct_val,
                    "is_correct": is_correct,
                    "explanation": q["explanation"],
                    "source_name": q["source_name"],
                })

            total = len(questions)
            pct = round((score / total) * 100, 1) if total else 0
            if pct >= 85:
                lvl = "Exceptional Consumer Awareness"
                msg = "Outstanding! You demonstrate strong mastery of statutory consumer rights under CPA 2019, statutory forums, limitation periods, and turnaround times."
            elif pct >= 60:
                lvl = "Good Practical Awareness"
                msg = "Good knowledge! You understand foundational consumer protections, but reviewing e-Jagriti commission procedures and pecuniary limits will make you fully prepared."
            else:
                lvl = "Foundational / Needs Review"
                msg = "Foundational stage. We strongly recommend exploring the 6 Statutory Rights and problem-specific issue guides on this portal to safeguard your marketplace rights."

            results = {
                "score": score,
                "total": total,
                "percentage": pct,
                "level": lvl,
                "message": msg,
                "breakdown": breakdown,
            }

        return render_template(
            "quiz.html",
            questions=questions,
            results=results,
            user_answers=user_answers,
        )

    @app.route("/about")
    def about():
        """Academic project overview, objectives, methodology, and legal framework."""
        return render_template("about.html")

    @app.route("/privacy")
    def privacy():
        """Privacy and data-handling explanation emphasizing public service and anonymity."""
        return render_template("privacy.html")

    @app.route("/feedback", methods=["GET", "POST"])
    def feedback():
        """Anonymous user feedback collection with strict privacy and input validation."""
        if request.method == "POST":
            feedback_type = request.form.get("feedback_type", "").strip()
            message = request.form.get("message", "").strip()
            page_url = request.form.get("page_url", "").strip()
            rating_raw = request.form.get("rating", "")

            # Strict Allowed Category Validation
            allowed_types = ("usability_suggestion", "content_correction", "portal_compliment", "general_feedback")
            if feedback_type not in allowed_types:
                flash("Please choose a valid feedback category from the list.", "error")
                return render_template("feedback.html", form_data=request.form)

            # Message Length Enforcements
            if not message or len(message) < 5:
                flash("Please provide a constructive message (at least 5 characters).", "error")
                return render_template("feedback.html", form_data=request.form)

            if len(message) > 1000:
                flash("Feedback message cannot exceed 1000 characters.", "error")
                return render_template("feedback.html", form_data=request.form)

            # Sensitive Data Protection Filter (Aadhaar / Card / Phone checks)
            has_aadhaar = re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\b", message)
            has_card = re.search(r"\b(?:\d{4}[-\s]?){3}\d{4}\b", message)
            has_phone = re.search(r"\b[6-9]\d{9}\b", message)
            if has_aadhaar or has_card or has_phone:
                flash("For your security and privacy, please do NOT include personal identity numbers, card details, or phone numbers in anonymous feedback.", "error")
                return render_template("feedback.html", form_data=request.form)

            # Rating Sanitization
            rating = None
            if rating_raw and rating_raw.isdigit():
                val = int(rating_raw)
                if 1 <= val <= 5:
                    rating = val

            # URL sanitization
            if len(page_url) > 255:
                page_url = page_url[:255]

            database = db.get_db()
            database.execute(
                """
                INSERT INTO feedback (feedback_type, message, page_url, rating)
                VALUES (?, ?, ?, ?)
                """,
                (feedback_type, message, page_url, rating),
            )
            database.commit()

            flash("Thank you for your valuable feedback! Your submission is completely anonymous and helps improve public consumer awareness.", "success")
            return redirect(url_for("feedback"))

        return render_template("feedback.html", form_data={})

    # -------------------------------------------------------------
    # PROTECTED ADMINISTRATIVE DASHBOARD
    # -------------------------------------------------------------

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        """Administrative login form with strict gating when unconfigured."""
        admin_user = app.config.get("ADMIN_USERNAME")
        admin_pass = app.config.get("ADMIN_PASSWORD")
        is_configured = bool(admin_user and admin_pass)

        if not is_configured:
            # Login disabled; display educational security disclosure
            return render_template("admin_login.html", disabled=True)

        if request.method == "POST":
            input_user = request.form.get("username", "").strip()
            input_pass = request.form.get("password", "")

            user_match = hmac.compare_digest(input_user.encode("utf-8"), admin_user.encode("utf-8"))
            pass_match = hmac.compare_digest(input_pass.encode("utf-8"), admin_pass.encode("utf-8"))

            if user_match and pass_match:
                session["is_admin"] = True
                session.permanent = False
                flash("Administrator session authenticated successfully.", "success")
                return redirect(url_for("admin_sources"))
            else:
                flash("Invalid administrator credentials. Please try again.", "error")
                return render_template("admin_login.html", disabled=False)

        return render_template("admin_login.html", disabled=False)

    @app.route("/admin/logout", methods=["GET", "POST"])
    def admin_logout():
        """Terminate administrator session."""
        session.pop("is_admin", None)
        flash("You have been signed out of the administrative review dashboard.", "success")
        return redirect(url_for("admin_login"))

    @app.route("/admin/sources")
    @admin_required
    def admin_sources():
        """Protected source-review and provenance health dashboard."""
        database = db.get_db()
        sources = database.execute(
            """
            SELECT s.*,
                   (SELECT COUNT(*) FROM rights WHERE source_id = s.id) as rights_count,
                   (SELECT COUNT(*) FROM issue_guides WHERE source_id = s.id) as guides_count,
                   (SELECT COUNT(*) FROM faqs WHERE source_id = s.id) as faqs_count,
                   c.status_code as last_status_code,
                   c.status_message as last_status_message,
                   c.response_time_ms as last_response_time_ms,
                   c.checked_at as last_checked_at
            FROM sources s
            LEFT JOIN source_checks c ON c.id = (
                SELECT id FROM source_checks WHERE source_id = s.id ORDER BY checked_at DESC LIMIT 1
            )
            ORDER BY s.id
            """
        ).fetchall()

        audit_logs = database.execute(
            """
            SELECT a.*, s.code as source_code, s.name as source_name
            FROM source_audit_logs a
            JOIN sources s ON a.source_id = s.id
            ORDER BY a.created_at DESC
            LIMIT 20
            """
        ).fetchall()

        metrics = {
            "total_sources": len(sources),
            "verified": sum(1 for s in sources if s["verification_status"] == "verified"),
            "pending": sum(1 for s in sources if s["verification_status"] == "pending_verification"),
            "needs_review": sum(1 for s in sources if s["verification_status"] == "needs_review"),
            "unavailable": sum(1 for s in sources if s["verification_status"] == "unavailable"),
        }

        return render_template("admin_sources.html", sources=sources, audit_logs=audit_logs, metrics=metrics)

    @app.route("/admin/sources/update", methods=["POST"])
    @admin_required
    def admin_source_update():
        """Update source review metadata and log audit action."""
        source_id = request.form.get("source_id", "").strip()
        new_status = request.form.get("verification_status", "").strip()
        notes = request.form.get("notes", "").strip()

        allowed_statuses = ("verified", "pending_verification", "needs_review", "unavailable")
        if not source_id.isdigit() or new_status not in allowed_statuses:
            flash("Invalid source ID or verification status.", "error")
            return redirect(url_for("admin_sources"))

        database = db.get_db()
        current = database.execute("SELECT verification_status FROM sources WHERE id = ?", (int(source_id),)).fetchone()
        if not current:
            flash("Source record not found.", "error")
            return redirect(url_for("admin_sources"))

        prev_status = current["verification_status"]

        database.execute(
            """
            UPDATE sources
            SET verification_status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_status, notes, int(source_id)),
        )

        database.execute(
            """
            INSERT INTO source_audit_logs (source_id, previous_status, new_status, notes, action_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (int(source_id), prev_status, new_status, notes, "admin"),
        )
        database.commit()

        flash(f"Source verification status updated from [{prev_status}] to [{new_status}]. Action recorded in audit logs.", "success")
        return redirect(url_for("admin_sources"))

    # -------------------------------------------------------------
    # API ENDPOINTS
    # -------------------------------------------------------------

    @app.route("/api/search")
    def api_search():
        """Search endpoint returning matching rights, issue guides, FAQs, and resources as JSON."""
        query = request.args.get("q", "").strip()
        type_filter = request.args.get("type", "all").strip().lower()
        if type_filter not in ("all", "right", "guide", "faq", "resource"):
            type_filter = "all"
        category_filter = request.args.get("category", "").strip()

        if not query or len(query) < 2:
            return jsonify({
                "query": query,
                "count": 0,
                "type_filter": type_filter,
                "category_filter": category_filter,
                "results": [],
                "message": "Search query must be at least 2 characters long."
            })

        database = db.get_db()
        results = search_content(
            database=database,
            raw_query=query,
            type_filter=type_filter,
            category_filter=category_filter or None,
            limit=20,
        )

        return jsonify({
            "query": query,
            "count": len(results),
            "type_filter": type_filter,
            "category_filter": category_filter,
            "results": results,
        })

    @app.route("/api/guides")
    def api_guides():
        """API returning published guidance records in JSON format."""
        database = db.get_db()
        guides = database.execute(
            """
            SELECT g.id, g.slug, g.title, g.category, g.summary, g.typical_situation, g.problem_statement,
                   g.step_by_step_procedure, g.required_evidence, g.evidence_checklist, g.relevant_legal_rights,
                   g.official_remedy_channel, g.caveats_and_escalation, g.verification_status, g.last_reviewed_at,
                   s.code as source_code, s.name as source_name, s.organisation as source_org
            FROM issue_guides g
            JOIN sources s ON g.source_id = s.id
            WHERE g.is_published = 1
            ORDER BY g.category, g.title
            """
        ).fetchall()

        output = []
        for row in guides:
            item = dict(row)
            try:
                item["step_by_step_procedure"] = json.loads(item["step_by_step_procedure"])
            except Exception:
                pass
            try:
                item["required_evidence"] = json.loads(item["required_evidence"])
            except Exception:
                pass
            try:
                item["evidence_checklist"] = json.loads(item["evidence_checklist"])
            except Exception:
                pass
            try:
                item["relevant_legal_rights"] = json.loads(item["relevant_legal_rights"])
            except Exception:
                pass
            output.append(item)

        return jsonify({
            "count": len(output),
            "guides": output
        })

    @app.route("/api/guides/<slug>")
    def api_guide_detail(slug):
        """API endpoint returning a single published guidance record by slug."""
        database = db.get_db()
        guide = database.execute(
            """
            SELECT g.id, g.slug, g.title, g.category, g.summary, g.typical_situation, g.problem_statement,
                   g.step_by_step_procedure, g.required_evidence, g.evidence_checklist, g.relevant_legal_rights,
                   g.official_remedy_channel, g.caveats_and_escalation, g.verification_status, g.last_reviewed_at,
                   s.code as source_code, s.name as source_name, s.organisation as source_org, s.url as source_url
            FROM issue_guides g
            JOIN sources s ON g.source_id = s.id
            WHERE g.slug = ? AND g.is_published = 1
            """,
            (slug,),
        ).fetchone()

        if not guide:
            return jsonify({"error": "Guide not found", "slug": slug}), 404

        item = dict(guide)
        try:
            item["step_by_step_procedure"] = json.loads(item["step_by_step_procedure"])
        except Exception:
            pass
        try:
            item["required_evidence"] = json.loads(item["required_evidence"])
        except Exception:
            pass
        try:
            item["evidence_checklist"] = json.loads(item["evidence_checklist"])
        except Exception:
            pass
        try:
            item["relevant_legal_rights"] = json.loads(item["relevant_legal_rights"])
        except Exception:
            pass

        return jsonify(item)

    @app.route("/api/resources")
    def api_resources():
        """API returning official government and dispute resolution services."""
        database = db.get_db()
        sources = database.execute(
            """
            SELECT s.id, s.code, s.name, s.organisation, s.authority, s.url,
                   s.domain, s.topic, s.source_type, s.summary, s.verification_status,
                   s.last_verified_at, s.verified_claims_or_topics
            FROM sources s
            ORDER BY s.id
            """
        ).fetchall()

        output = []
        for s in sources:
            item = dict(s)
            try:
                item["verified_claims_or_topics"] = json.loads(item["verified_claims_or_topics"])
            except Exception:
                pass
            output.append(item)

        return jsonify({
            "count": len(output),
            "resources": output,
        })

    @app.route("/api/quiz/submit", methods=["POST"])
    def api_quiz_submit():
        """Calculate quiz results on the backend against database records."""
        data = request.get_json(silent=True) or {}
        answers = data.get("answers", {})

        database = db.get_db()
        questions = database.execute(
            """
            SELECT q.*, s.name as source_name, s.code as source_code
            FROM quiz_questions q
            LEFT JOIN sources s ON q.source_id = s.id
            ORDER BY q.id
            """
        ).fetchall()

        total = len(questions)
        score = 0
        breakdown = []

        for q in questions:
            qid_str = str(q["id"])
            user_opt = (answers.get(qid_str) or "").strip().upper()
            correct_opt = q["correct_option"].strip().upper()
            is_correct = (user_opt == correct_opt)
            if is_correct:
                score += 1

            breakdown.append({
                "id": q["id"],
                "question": q["question"],
                "scenario": q["scenario"],
                "user_answer": user_opt if user_opt else None,
                "correct_option": correct_opt,
                "is_correct": is_correct,
                "explanation": q["explanation"],
                "source_name": q["source_name"],
            })

        percentage = round((score / total) * 100, 1) if total else 0
        if percentage >= 85:
            awareness_level = "Exceptional Consumer Awareness"
            summary_message = "Outstanding! You demonstrate strong mastery of statutory consumer rights under CPA 2019, statutory forums, limitation periods, and turnaround times."
        elif percentage >= 60:
            awareness_level = "Good Practical Awareness"
            summary_message = "Good knowledge! You understand foundational consumer protections, but reviewing e-Jagriti commission procedures and pecuniary limits will make you fully prepared."
        else:
            awareness_level = "Foundational / Needs Review"
            summary_message = "Foundational stage. We strongly recommend exploring the 6 Statutory Rights and problem-specific issue guides on this portal to safeguard your marketplace rights."

        return jsonify({
            "score": score,
            "total": total,
            "percentage": percentage,
            "awareness_level": awareness_level,
            "summary_message": summary_message,
            "results": breakdown,
        })

    @app.route("/api/feedback", methods=["POST"])
    def api_feedback():
        """JSON endpoint for anonymous feedback submission with backend validation."""
        data = request.get_json(silent=True) or {}
        feedback_type = (data.get("feedback_type") or "").strip()
        message = (data.get("message") or "").strip()
        page_url = (data.get("page_url") or "").strip()
        rating_raw = data.get("rating")

        allowed_types = ("usability_suggestion", "content_correction", "portal_compliment", "general_feedback")
        if feedback_type not in allowed_types:
            return jsonify({"error": "Invalid feedback category", "field": "feedback_type"}), 400

        if not message or len(message) < 5:
            return jsonify({"error": "Message must be at least 5 characters long", "field": "message"}), 400

        if len(message) > 1000:
            return jsonify({"error": "Message exceeds maximum 1000 characters limit", "field": "message"}), 400

        # Sensitive Data Protection Filter
        has_aadhaar = re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\b", message)
        has_card = re.search(r"\b(?:\d{4}[-\s]?){3}\d{4}\b", message)
        has_phone = re.search(r"\b[6-9]\d{9}\b", message)
        if has_aadhaar or has_card or has_phone:
            return jsonify({
                "error": "For your security and privacy, please do NOT include personal identity numbers, card details, or phone numbers in anonymous feedback.",
                "field": "message"
            }), 400

        rating = None
        if rating_raw is not None:
            try:
                val = int(rating_raw)
                if 1 <= val <= 5:
                    rating = val
            except (ValueError, TypeError):
                pass

        if len(page_url) > 255:
            page_url = page_url[:255]

        database = db.get_db()
        database.execute(
            """
            INSERT INTO feedback (feedback_type, message, page_url, rating)
            VALUES (?, ?, ?, ?)
            """,
            (feedback_type, message, page_url, rating),
        )
        database.commit()

        return jsonify({
            "success": True,
            "message": "Thank you for your valuable feedback! Your submission is anonymous and helps improve public consumer awareness."
        })

    # -------------------------------------------------------------
    # CUSTOM ERROR HANDLERS (HTML and JSON)
    # -------------------------------------------------------------

    @app.errorhandler(404)
    def page_not_found(e):
        if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
            return jsonify({"error": "Resource not found", "status_code": 404}), 404
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
            return jsonify({"error": "Internal server error", "status_code": 500}), 500
        return render_template("500.html"), 500

    return app

# Expose default WSGI application callable for production WSGI servers (Gunicorn on Render)
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1")
    is_prod = os.environ.get("FLASK_ENV") == "production" or os.environ.get("RENDER") is not None
    app.run(host=host, port=port, debug=not is_prod)

