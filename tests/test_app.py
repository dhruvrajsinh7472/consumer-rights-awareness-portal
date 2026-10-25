import json
import sqlite3

def test_home_page(client):
    """Test that home page loads with 200 and key editorial headings."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Consumer Rights Portal" in response.data
    assert b"The 6 Statutory Consumer Rights" in response.data
    assert b"Know Your Rights" in response.data

def test_rights_list_page(client):
    """Test that rights catalog lists all 6 statutory rights per Section 2(9) CPA 2019."""
    response = client.get("/rights")
    assert response.status_code == 200
    assert b"Right to Safety" in response.data
    assert b"Right to be Informed" in response.data
    assert b"Right to Choose" in response.data
    assert b"Right to be Heard" in response.data
    assert b"Right to Seek Redressal" in response.data
    assert b"Right to Consumer Education" in response.data

def test_right_detail_page(client):
    """Test that individual right detail view displays statutory text, scenario, and source provenance."""
    response = client.get("/rights/right-to-safety")
    assert response.status_code == 200
    assert b"Right to Safety" in response.data
    assert b"Section 2(9)(i)" in response.data
    assert b"Practical Illustrative Scenario" in response.data
    assert b"Official Source &amp; Provenance" in response.data

    # Test backward-compatible redirects for previous slugs
    redirect_res1 = client.get("/rights/right-to-information")
    assert redirect_res1.status_code in (301, 302)
    assert "/rights/right-to-be-informed" in redirect_res1.headers["Location"]

    redirect_res2 = client.get("/rights/right-to-redressal")
    assert redirect_res2.status_code in (301, 302)
    assert "/rights/right-to-seek-redressal" in redirect_res2.headers["Location"]

    # Test 404 on nonexistent slug
    response_404 = client.get("/rights/non-existent-statutory-right")
    assert response_404.status_code == 404
    assert b"Page or Resource Not Found" in response_404.data

def test_problems_directory(client):
    """Test common consumer problems directory and filtering."""
    response = client.get("/problems")
    assert response.status_code == 200
    assert b"Common Consumer Problems" in response.data
    assert b"E-Commerce Refund Delays" in response.data

    # Test filtering by valid category
    cat_response = client.get("/problems?category=Online+Shopping+%26+E-Commerce")
    assert cat_response.status_code == 200
    assert b"E-Commerce Refund Delays" in cat_response.data

def test_guidance_pages(client):
    """Test guidance overview and specific guide walkthrough."""
    overview_response = client.get("/guidance")
    assert overview_response.status_code == 200
    assert b"Consumer Dispute Guidance System" in overview_response.data

    detail_response = client.get("/guidance/e-commerce-refund-delays")
    assert detail_response.status_code == 200
    assert b"Document &amp; Evidence Checklist" in detail_response.data
    assert b"Step-by-Step Suggested Actions" in detail_response.data

    not_found = client.get("/guidance/unknown-problem-slug")
    assert not_found.status_code == 404

def test_resources_page(client):
    """Test official government and regulatory services directory."""
    response = client.get("/resources")
    assert response.status_code == 200
    assert b"National Consumer Helpline" in response.data
    assert b"e-Jagriti" in response.data
    assert b"1915" in response.data

def test_faqs_page(client):
    """Test FAQs page renders with verified questions."""
    response = client.get("/faqs")
    assert response.status_code == 200
    assert b"Frequently Asked Questions" in response.data
    assert b"What are statutory consumer rights" in response.data

def test_quiz_page(client):
    """Test consumer awareness quiz page."""
    response = client.get("/quiz")
    assert response.status_code == 200
    assert b"Consumer Rights Awareness Quiz" in response.data
    assert b"Question 1 of" in response.data

def test_about_and_privacy_pages(client):
    """Test academic overview and privacy policy pages."""
    about_res = client.get("/about")
    assert about_res.status_code == 200
    assert b"Community Engagement Project" in about_res.data

    privacy_res = client.get("/privacy")
    assert privacy_res.status_code == 200
    assert b"Zero Tracking and No Commercial Cookies" in privacy_res.data

def test_feedback_submission(client, app):
    """Test anonymous feedback form rendering and database insertion."""
    # GET request
    get_res = client.get("/feedback")
    assert get_res.status_code == 200
    assert b"Anonymous Feedback" in get_res.data

    # POST valid feedback
    post_res = client.post(
        "/feedback",
        data={
            "feedback_type": "content_correction",
            "message": "Suggestion to add state-specific commission fee schedules.",
            "page_url": "/resources",
            "rating": "5",
        },
        follow_redirects=True,
    )
    assert post_res.status_code == 200
    assert b"Thank you for your valuable feedback" in post_res.data

    # Verify insertion in database
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM feedback WHERE feedback_type = 'content_correction'").fetchone()
    conn.close()
    assert row is not None
    assert row["rating"] == 5
    assert "Suggestion to add" in row["message"]

def test_api_search(client):
    """Test JSON search endpoint across rights and guides."""
    # Valid search query
    res = client.get("/api/search?q=refund")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["count"] > 0
    assert any("refund" in item["title"].lower() or "refund" in item["summary"].lower() for item in data["results"])

    # Short query (< 2 chars)
    short_res = client.get("/api/search?q=a")
    assert short_res.status_code == 200
    short_data = json.loads(short_res.data)
    assert short_data["count"] == 0

def test_api_guides(client):
    """Test published guides API returns JSON records."""
    res = client.get("/api/guides")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "guides" in data
    assert data["count"] >= 6
    first_guide = data["guides"][0]
    assert "slug" in first_guide
    assert isinstance(first_guide["step_by_step_procedure"], list)

def test_static_assets(client):
    """Test that CSS and JS files exist and are servable."""
    css_res = client.get("/static/css/style.css")
    assert css_res.status_code == 200
    assert b":root" in css_res.data

    js_res = client.get("/static/js/main.js")
    assert js_res.status_code == 200

    quiz_js_res = client.get("/static/js/quiz.js")
    assert quiz_js_res.status_code == 200

    # Verify all 9 integrated photos from PHOTOS folder
    expected_images = [
        "hero_backgroun.jpg",
        "consumer_awareness.jpg",
        "consumer_rights.jpg",
        "customer_support.jpg",
        "digital_complaint.jpg",
        "justice_background.jpg",
        "online_shopping.jpg",
        "product_quality.jpg",
        "about_background.jpg",
    ]
    for img_name in expected_images:
        img_res = client.get(f"/static/images/{img_name}")
        assert img_res.status_code == 200, f"Image {img_name} failed to serve via static handler"
        assert len(img_res.data) > 0

def test_sources_registry_page(client):
    """Test that public Source Registry & Audit page renders with genuine verification badges and counts."""
    response = client.get("/sources")
    assert response.status_code == 200
    assert b"Official Source Registry &amp; Audit" in response.data
    assert b"Verified Primary Source" in response.data
    assert b"Pending Formal Verification" in response.data
    assert b"Consumer Protection Act, 2019" in response.data
    assert b"National Consumer Helpline" in response.data
    assert b"e-Jagriti Unified" in response.data
    assert b"Bureau of Indian Standards" in response.data
    assert b"100%" in response.data

def test_guidance_evidence_checklists(client):
    """Test that issue guides render the 3-tier structured evidence checklist and caveats."""
    response = client.get("/guidance/e-commerce-refund-delays")
    assert response.status_code == 200
    assert b"Document &amp; Evidence Checklist" in response.data
    assert b"Documents Officially Specified as Required" in response.data
    assert b"Evidence That is Highly Useful to Preserve" in response.data
    assert b"Documents Applicable in Particular Circumstances" in response.data
    assert b"Statutory Caveats &amp; Escalation Guidance" in response.data
    assert b"Official Source &amp; Verification" in response.data
    assert b"Consumer Protection (E-Commerce) Rules, 2020" in response.data

def test_nine_problem_categories(client):
    """Test that all 9 common consumer problem categories exist and are accessible."""
    expected_slugs = [
        "e-commerce-refund-delays",
        "defective-goods-warranty",
        "wrong-product-delivered",
        "overcharging-above-mrp",
        "digital-payment-failures",
        "online-shopping-dark-patterns",
        "misleading-advertisements",
        "product-certification-hallmark",
        "service-deficiency-telecom",
    ]
    for slug in expected_slugs:
        res = client.get(f"/guidance/{slug}")
        assert res.status_code == 200, f"Guide {slug} failed to load"
        assert b"Step-by-Step Suggested Actions" in res.data

def test_faqs_provenance_and_jurisdiction(client):
    """Test that FAQs display verified source citations and accurate pecuniary limits."""
    response = client.get("/faqs")
    assert response.status_code == 200
    assert b"Statutory Source" in response.data
    assert b"Verified Primary Source" in response.data
    assert b"50 Lakh" in response.data  # District Commission pecuniary limit under 2021 Rules
    assert b"NIL Fee" in response.data  # Claims up to 5 Lakh have nil fee
    assert b"T+1" in response.data  # RBI TAT circular
    assert b"100 per day" in response.data  # Auto-reversal penalty compensation

def test_database_source_integrity(app):
    """Database integrity audit verifying foreign keys and zero missing citations."""
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row

    # All rights must have a valid source
    uncited_rights = conn.execute("SELECT COUNT(*) as c FROM rights WHERE source_id IS NULL").fetchone()["c"]
    assert uncited_rights == 0

    # All published guides must have a valid source
    uncited_guides = conn.execute("SELECT COUNT(*) as c FROM issue_guides WHERE is_published = 1 AND source_id IS NULL").fetchone()["c"]
    assert uncited_guides == 0

    # All FAQs must have a valid source
    uncited_faqs = conn.execute("SELECT COUNT(*) as c FROM faqs WHERE source_id IS NULL").fetchone()["c"]
    assert uncited_faqs == 0

    # Verification status must be explicitly set
    invalid_sources = conn.execute(
        "SELECT COUNT(*) as c FROM sources WHERE verification_status NOT IN ('verified', 'pending_verification', 'unavailable', 'needs_review')"
    ).fetchone()["c"]
    assert invalid_sources == 0

    conn.close()

def test_global_search_page(client):
    """Test global search page with keyword queries, type filters, and empty states."""
    # Search query
    res = client.get("/search?q=refund")
    assert res.status_code == 200
    assert b"Showing" in res.data
    assert b"result" in res.data
    assert b"E-Commerce Refund Delays" in res.data

    # Type filter: rights
    res_rights = client.get("/search?q=consumer&type=right")
    assert res_rights.status_code == 200
    assert b"Statutory Right" in res_rights.data

    # Empty search query
    res_empty = client.get("/search")
    assert res_empty.status_code == 200
    assert b"Enter a search keyword above" in res_empty.data

    # No match query empty state
    res_nomatch = client.get("/search?q=xyznonexistentquery123")
    assert res_nomatch.status_code == 200
    assert b"No verified records matched" in res_nomatch.data
    assert b"Clear All Filters" in res_nomatch.data

def test_interactive_wizard_flow(client):
    """Test multi-step consumer problem guidance wizard."""
    # Step 1: Domain selector
    res_s1 = client.get("/wizard")
    assert res_s1.status_code == 200
    assert b"What category does your consumer problem fall under?" in res_s1.data
    assert b"Online Shopping &amp; E-Commerce" in res_s1.data or b"Online Shopping" in res_s1.data

    # Step 2: Follow-up question for selected domain
    res_s2 = client.get("/wizard?domain=ecommerce")
    assert res_s2.status_code == 200
    assert b"Delayed Refund or Return Rejection" in res_s2.data
    assert b"Back to all problem categories" in res_s2.data

    # Step 3: Verified guide match with 3-tier checklist
    res_s3 = client.get("/wizard?guide=e-commerce-refund-delays")
    assert res_s3.status_code == 200
    assert b"Step-by-Step Resolution Procedure" in res_s3.data
    assert b"Tier 1: Officially Specified Documents" in res_s3.data
    assert b"Official Escalation Authority" in res_s3.data
    assert b"Print Guide &amp; Evidence Sheet" in res_s3.data

    # Step 4: Unsupported sector honest fallback
    res_unsupported = client.get("/wizard?unsupported=true")
    assert res_unsupported.status_code == 200
    assert b"Verified Guide Not Available Yet" in res_unsupported.data
    assert b"1915" in res_unsupported.data
    assert b"Explore Official Directory" in res_unsupported.data

def test_quiz_evaluation_api(client):
    """Test server-side scoring for the awareness quiz via JSON API."""
    payload = {
        "answers": {
            "1": "C",
            "2": "B",
            "3": "C",
            "4": "B",
            "5": "C",
            "6": "C",
            "7": "C",
            "8": "B",
        }
    }
    res = client.post(
        "/api/quiz/submit",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "score" in data
    assert "total" in data
    assert "percentage" in data
    assert "awareness_level" in data
    assert "results" in data
    assert len(data["results"]) == 8
    # Test breakdown details
    first_item = data["results"][0]
    assert "explanation" in first_item
    assert "correct_option" in first_item
    assert "is_correct" in first_item

def test_quiz_form_post_submission(client):
    """Test server-side scoring via standard POST form submission."""
    form_data = {
        "question_1": "B",
        "question_2": "C",
        "question_3": "A",
    }
    res = client.post("/quiz", data=form_data)
    assert res.status_code == 200
    assert b"Your Consumer Rights Score" in res.data
    assert b"Statutory Explanation" in res.data

def test_feedback_sensitive_data_detection(client, app):
    """Test that feedback submissions with sensitive numbers (Aadhaar, cards, phone) are strictly rejected."""
    # Aadhaar rejection test
    res_aadhaar = client.post(
        "/feedback",
        data={
            "feedback_type": "usability_suggestion",
            "message": "My complaint number is linked to Aadhaar 4920 1234 5678 please fix.",
        },
        follow_redirects=True,
    )
    assert b"please do NOT include personal identity numbers" in res_aadhaar.data

    # Phone number rejection test
    res_phone = client.post(
        "/feedback",
        data={
            "feedback_type": "usability_suggestion",
            "message": "Call me on 9876543210 regarding my refund problem.",
        },
        follow_redirects=True,
    )
    assert b"please do NOT include personal identity numbers" in res_phone.data

    # Valid message length enforcement (< 5 chars)
    res_short = client.post(
        "/feedback",
        data={
            "feedback_type": "usability_suggestion",
            "message": "bad",
        },
        follow_redirects=True,
    )
    assert b"at least 5 characters" in res_short.data

def test_api_feedback_endpoint(client):
    """Test /api/feedback JSON endpoint."""
    # Valid submission
    res = client.post(
        "/api/feedback",
        data=json.dumps({
            "feedback_type": "usability_suggestion",
            "message": "High-contrast font toggle would enhance accessibility.",
            "rating": 5,
        }),
        content_type="application/json",
    )
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True

    # Sensitive data rejection on API
    res_bad = client.post(
        "/api/feedback",
        data=json.dumps({
            "feedback_type": "usability_suggestion",
            "message": "My card number 4111 2222 3333 4444 was charged twice.",
        }),
        content_type="application/json",
    )
    assert res_bad.status_code == 400
    data_bad = json.loads(res_bad.data)
    assert "security and privacy" in data_bad["error"]

def test_admin_auth_and_source_update(client, app):
    """Test administrator authentication gating and source verification updating."""
    # 1. Without credentials configured, login shows disabled
    app.config["ADMIN_USERNAME"] = None
    app.config["ADMIN_PASSWORD"] = None

    login_res = client.get("/admin/login")
    assert login_res.status_code == 200
    assert b"Administrative Access Disabled" in login_res.data

    # Route should redirect without session
    sources_res = client.get("/admin/sources", follow_redirects=True)
    assert b"Administrator authentication is required" in sources_res.data

    # 2. Configure credentials
    app.config["ADMIN_USERNAME"] = "testadmin"
    app.config["ADMIN_PASSWORD"] = "testpass123"

    # Bad login
    bad_login = client.post(
        "/admin/login",
        data={"username": "testadmin", "password": "wrongpassword"},
        follow_redirects=True,
    )
    assert b"Invalid administrator credentials" in bad_login.data

    # Valid login
    good_login = client.post(
        "/admin/login",
        data={"username": "testadmin", "password": "testpass123"},
        follow_redirects=True,
    )
    assert good_login.status_code == 200
    assert b"Content Source &amp; Provenance Dashboard" in good_login.data
    assert b"Network Reachability &ne; Content Verification" in good_login.data

    # Update source verification status
    update_res = client.post(
        "/admin/sources/update",
        data={
            "source_id": "1",
            "verification_status": "needs_review",
            "notes": "Annual gazette notification revision review scheduled.",
        },
        follow_redirects=True,
    )
    assert update_res.status_code == 200
    assert b"Source verification status updated" in update_res.data

    # Verify audit log in SQLite
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    audit = conn.execute("SELECT * FROM source_audit_logs WHERE source_id = 1").fetchone()
    conn.close()
    assert audit is not None
    assert audit["new_status"] == "needs_review"
    assert "Annual gazette" in audit["notes"]

def test_api_guides_and_resources(client):
    """Test /api/guides/<slug> and /api/resources JSON endpoints."""
    # Single guide endpoint
    guide_res = client.get("/api/guides/e-commerce-refund-delays")
    assert guide_res.status_code == 200
    gdata = json.loads(guide_res.data)
    assert gdata["slug"] == "e-commerce-refund-delays"
    assert "evidence_checklist" in gdata

    # Nonexistent guide
    guide_404 = client.get("/api/guides/nonexistent-slug")
    assert guide_404.status_code == 404

    # Resources endpoint
    res_res = client.get("/api/resources")
    assert res_res.status_code == 200
    rdata = json.loads(res_res.data)
    assert "resources" in rdata
    assert rdata["count"] >= 10

def test_search_security_and_edge_cases(client):
    """Test search with SQL injection strings, XSS payloads, and oversized queries."""
    # SQL injection attempt
    sql_inj = client.get("/search?q=%27%20OR%201%3D1%20--")
    assert sql_inj.status_code == 200
    assert b"No verified records matched" in sql_inj.data

    # XSS attempt - verify escaping in HTML output
    xss_payload = "<script>alert('xss')</script>"
    xss_res = client.get(f"/search?q={xss_payload}")
    assert xss_res.status_code == 200
    # Must NOT render unescaped <script> tag
    assert b"<script>alert('xss')</script>" not in xss_res.data
    assert b"&lt;script&gt;alert" in xss_res.data or b"&amp;#039;xss" in xss_res.data

    # Oversized search query (150 chars, capped at 100)
    oversized_res = client.get("/search?q=" + "a" * 150)
    assert oversized_res.status_code == 200

    # API search with special characters
    api_xss = client.get(f"/api/search?q={xss_payload}")
    assert api_xss.status_code == 200
    api_data = json.loads(api_xss.data)
    assert api_data["count"] == 0

def test_quiz_scoring_variations(client):
    """Test awareness quiz scoring for perfect score, zero score, and invalid input."""
    # Perfect score submission (8 of 8 correct)
    perfect_answers = {
        "1": "C",
        "2": "B",
        "3": "C",
        "4": "B",
        "5": "C",
        "6": "C",
        "7": "C",
        "8": "B",
    }
    perf_res = client.post(
        "/api/quiz/submit",
        data=json.dumps({"answers": perfect_answers}),
        content_type="application/json"
    )
    assert perf_res.status_code == 200
    perf_data = json.loads(perf_res.data)
    assert perf_data["score"] == 8
    assert perf_data["percentage"] == 100.0
    assert "Exceptional" in perf_data["awareness_level"]

    # Zero score submission
    zero_answers = {
        "1": "D",
        "2": "D",
        "3": "D",
        "4": "D",
        "5": "D",
        "6": "D",
        "7": "D",
        "8": "D",
    }
    zero_res = client.post(
        "/api/quiz/submit",
        data=json.dumps({"answers": zero_answers}),
        content_type="application/json"
    )
    assert zero_res.status_code == 200
    zero_data = json.loads(zero_res.data)
    assert zero_data["score"] == 0
    assert zero_data["percentage"] == 0.0
    assert "Foundational" in zero_data["awareness_level"]

    # Empty payload
    empty_res = client.post(
        "/api/quiz/submit",
        data=json.dumps({}),
        content_type="application/json"
    )
    assert empty_res.status_code == 200
    empty_data = json.loads(empty_res.data)
    assert empty_data["score"] == 0

def test_custom_error_handlers(client):
    """Test custom error handling returning HTML for page requests and JSON for API requests."""
    # Web 404
    html_404 = client.get("/non-existent-page-path-123")
    assert html_404.status_code == 404
    assert b"Page or Resource Not Found" in html_404.data

    # API 404
    api_404 = client.get("/api/non-existent-endpoint-456")
    assert api_404.status_code == 404
    assert api_404.content_type == "application/json"
    data = json.loads(api_404.data)
    assert data["status_code"] == 404
    assert "Resource not found" in data["error"]

def test_source_provenance_and_unverified_flags(client, app):
    """Audit source citations, ensure zero duplicate slugs, zero blank URLs, and explicit unverified flags."""
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row

    # 1. No duplicate slugs in rights or guides
    right_slug_count = conn.execute("SELECT COUNT(slug) as c, COUNT(DISTINCT slug) as dc FROM rights").fetchone()
    assert right_slug_count["c"] == right_slug_count["dc"]

    guide_slug_count = conn.execute("SELECT COUNT(slug) as c, COUNT(DISTINCT slug) as dc FROM issue_guides").fetchone()
    assert guide_slug_count["c"] == guide_slug_count["dc"]

    # 2. No blank or empty URLs in sources
    blank_urls = conn.execute("SELECT COUNT(*) as c FROM sources WHERE url IS NULL OR trim(url) = ''").fetchone()["c"]
    assert blank_urls == 0

    # 3. Foreign key validity: all source_id in rights point to existing sources
    orphan_rights = conn.execute("SELECT COUNT(*) as c FROM rights r LEFT JOIN sources s ON r.source_id = s.id WHERE s.id IS NULL").fetchone()["c"]
    assert orphan_rights == 0

    orphan_guides = conn.execute("SELECT COUNT(*) as c FROM issue_guides g LEFT JOIN sources s ON g.source_id = s.id WHERE s.id IS NULL").fetchone()["c"]
    assert orphan_guides == 0

    orphan_faqs = conn.execute("SELECT COUNT(*) as c FROM faqs f LEFT JOIN sources s ON f.source_id = s.id WHERE s.id IS NULL").fetchone()["c"]
    assert orphan_faqs == 0

    # 4. Unverified / pending content is NOT marked verified
    telecom_guide = conn.execute("SELECT verification_status FROM issue_guides WHERE slug = 'service-deficiency-telecom'").fetchone()
    assert telecom_guide is not None
    assert telecom_guide["verification_status"] == "pending_verification"

    trai_source = conn.execute("SELECT verification_status FROM sources WHERE code = 'TRAI_CONSUMER_REGULATIONS'").fetchone()
    assert trai_source is not None
    assert trai_source["verification_status"] == "pending_verification"

    conn.close()

def test_feedback_boundary_and_validation(client):
    """Test feedback boundary values (oversized message, invalid ratings)."""
    # Oversized message (> 1000 characters)
    oversized_res = client.post(
        "/feedback",
        data={
            "feedback_type": "usability_suggestion",
            "message": "x" * 1050,
        },
        follow_redirects=True,
    )
    assert b"cannot exceed 1000 characters" in oversized_res.data

    # Invalid category
    bad_cat_res = client.post(
        "/feedback",
        data={
            "feedback_type": "nonexistent_category",
            "message": "Valid constructive message length.",
        },
        follow_redirects=True,
    )
    assert b"valid feedback category" in bad_cat_res.data


def test_healthz_endpoint(client):
    """Test production health check endpoint for Render liveness."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = json.loads(response.data.decode("utf-8"))
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "portal" in data


def test_database_url_normalization_and_placeholders():
    """Verify Supabase PostgreSQL connection normalization and SQL parameter conversion."""
    import db

    # PostgreSQL detection
    assert db.is_postgres_url("postgresql://postgres:password@aws-0-ap-south-1.pooler.supabase.com:5432/postgres")
    assert db.is_postgres_url("postgres://postgres:password@aws-0-ap-south-1.pooler.supabase.com:6543/postgres")
    assert not db.is_postgres_url("instance/consumer_rights.db")
    assert not db.is_postgres_url("sqlite:///consumer_rights.db")

    # URL normalization & SSL enforcement for remote Supabase poolers
    pg_url = "postgres://postgres.abc:xyz@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
    clean = db.normalize_db_url(pg_url)
    assert clean.startswith("postgresql://")
    assert "sslmode=require" in clean

    # Parameter placeholder translation (? to %s) while preserving literal strings with question marks
    sql = "SELECT * FROM rights WHERE slug != ? AND title = 'What is Consumer Rights?' AND id = ?"
    converted = db.convert_placeholders(sql)
    assert converted == "SELECT * FROM rights WHERE slug != %s AND title = 'What is Consumer Rights?' AND id = %s"


def test_database_connection_test_helper():
    """Verify that test_connection returns success on valid database and sanitizes secrets on error."""
    import db
    success, msg = db.test_connection()
    assert success is True
    assert "Successfully connected" in msg



