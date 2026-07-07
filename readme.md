  SpamLens API Documentation   :root { --bg: #110E1F; --bg-elevated: #1A1631; --bg-input: #150F26; --fg: #EAEAFF; --fg-secondary: #A19BBF; --fg-muted: #5C567A; --accent: #8B5CF6; --accent-dim: rgba(139, 92, 246, 0.12); --accent-glow: rgba(139, 92, 246, 0.3); --danger: #F0465A; --danger-dim: rgba(240, 70, 90, 0.12); --safe: #34D399; --safe-dim: rgba(52, 211, 153, 0.12); --border: rgba(139, 92, 246, 0.1); --font-ui: 'DM Sans', sans-serif; --font-mono: 'JetBrains Mono', monospace; } \*, \*::before, \*::after { box-sizing: border-box; margin: 0; padding: 0; } body { font-family: var(--font-ui); background: var(--bg); color: var(--fg); line-height: 1.7; padding: 40px 20px; } .container { max-width: 850px; margin: 0 auto; animation: fade-in 0.6s ease; } @keyframes fade-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } } /\* Typography \*/ h1, h2, h3, h4 { color: var(--fg); margin-bottom: 16px; line-height: 1.3; } h1 { font-size: 2.5rem; font-weight: 900; letter-spacing: -1px; margin-bottom: 8px; background: linear-gradient(135deg, var(--fg), var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; } h2 { font-size: 1.5rem; font-weight: 700; margin-top: 48px; padding-bottom: 12px; border-bottom: 1px solid var(--border); } h3 { font-size: 1.15rem; font-weight: 600; margin-top: 32px; color: var(--accent); } p { margin-bottom: 16px; color: var(--fg-secondary); } strong { color: var(--fg); font-weight: 600; } a { color: var(--accent); text-decoration: none; font-weight: 500; transition: color 0.2s; } a:hover { text-decoration: underline; } hr { border: none; border-top: 1px solid var(--border); margin: 40px 0; } /\* Layout Elements \*/ .subtitle { font-size: 1.1rem; color: var(--fg-muted); margin-bottom: 40px; } ul { margin-bottom: 20px; padding-left: 24px; } li { margin-bottom: 8px; color: var(--fg-secondary); } li strong { color: var(--fg); } /\* Code Blocks \*/ pre { background: var(--bg-input); border: 1px solid var(--border); border-left: 4px solid var(--accent); border-radius: 8px; padding: 20px; overflow-x: auto; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); } code { font-family: var(--font-mono); font-size: 0.9rem; color: var(--fg); } p code, li code { font-family: var(--font-mono); background: var(--bg-elevated); padding: 2px 6px; border-radius: 4px; font-size: 0.85rem; color: var(--accent); } /\* Tables \*/ table { width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 0.95rem; } th, td { text-align: left; padding: 12px 16px; border-bottom: 1px solid var(--border); } th { background: var(--bg-elevated); color: var(--fg); font-weight: 600; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; } td { color: var(--fg-secondary); } tr:last-child td { border-bottom: none; } /\* Badges \*/ .badge { display: inline-block; font-size: 0.8rem; font-family: var(--font-mono); background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 6px; padding: 2px 8px; color: var(--fg-muted); margin-right: 8px; } .method { color: var(--safe); font-weight: 600; } .tag { color: var(--accent); } @media (max-width: 600px) { body { padding: 20px 16px; } h1 { font-size: 2rem; } pre { padding: 12px; font-size: 0.8rem; } th, td { padding: 8px 10px; font-size: 0.85rem; } }

SpamLens API Documentation
==========================

Enterprise-grade spam detection API combining a Soft Voting Ensemble Machine Learning model with a heuristic Rule Engine.

**Creator:** [MaximizeAy](https://github.com/MaximizeAy)

* * *

Table of Contents
-----------------

*   [Architecture Overview](#architecture)
*   [Endpoints](#endpoints)
*   [Authentication & Security](#auth)
*   [Response Schemas](#schemas)
*   [Fusion Logic (How it works)](#fusion)
*   [Local Development Setup](#setup)
*   [Load Testing](#load)

* * *

Architecture Overview
---------------------

SpamLens processes incoming text through two parallel pipelines to produce a single, fused verdict:

1.  **The ML Pipeline:** Extracts structural features (URL count, security keywords, urgency words) and passes them to a pre-trained Scikit-Learn Soft Voting Ensemble to get a probabilistic confidence score.
2.  **The Rule Engine:** Runs 11 heuristic checks (e.g., pharmaceutical keywords, excessive punctuation, impersonation signals) to generate a deterministic score based on pattern matching.
3.  **The Fusion Layer:** Dynamically weights the two scores based on confidence levels and safety overrides (e.g., if the ML model misses a pharmaceutical spam word, the rule engine overrides the verdict).

* * *

Endpoints
---------

### Analyze Single Email

Analyzes a single text string using the fused ML + Rule Engine logic.

*   URL `/analyze`
*   Method POST
*   Content-Type `application/json`

**Request Body:**

    {
      "text": "GET 80% OFF on all medications!!! Viagra, Cialis, Xanax — no prescription needed! Order now at www.cheap-pills.biz."
    }

**Response: 200 OK**

    {
      "final_verdict": "spam",
      "final_confidence": 91,
      "ml": {
        "prediction": "Spam",
        "internal_class": "spam",
        "confidence_pct": 97,
        "confidence_raw": 0.9788,
        "model": "Soft Voting Ensemble",
        "version": "1.0.0",
        "prediction_time_ms": 118.09,
        "features": {
          "has_url": true,
          "url_count": 1,
          "security_keyword_count": 0,
          "urgency_count": 0
        }
      },
      "rules": {
        "verdict": "spam",
        "confidence": 81,
        "features": [
          {
            "id": "pharma_keywords",
            "name": "Pharmaceutical Keywords",
            "desc": "1 pattern(s) matched",
            "icon": "fa-solid fa-pills",
            "score": 18,
            "severity": "high",
            "type": "flag"
          }
        ]
      },
      "strategy": "ml_primary",
      "override_reason": null,
      "meta": { "response_time_ms": 142 }
    }

### Analyze Batch

Analyzes an array of texts. Useful for processing log files or exported mailboxes.

*   URL `/analyze/batch`
*   Method POST
*   Content-Type `application/json`

**Request Body:**

    {
      "texts": [
        "Hi team, just a reminder about our Q4 planning meeting tomorrow.",
        "URGENT: Send 0.5 BTC to receive 1.0 BTC back in 24 hours GUARANTEED!!!"
      ]
    }

**Response: 200 OK**

    {
      "total": 2,
      "spam": 1,
      "suspicious": 0,
      "safe": 1,
      "results": [
        {
          "text": "Hi team, just a reminder about our Q4 planning meeting tomorrow.",
          "final_verdict": "safe",
          "final_confidence": 12,
          "ml": { "prediction": "Ham", "confidence_pct": 8 },
          "rules": { "verdict": "safe", "confidence": 15 },
          "strategy": "ml_primary"
        }
      ],
      "meta": { "response_time_ms": 240 }
    }

_Note: The batch endpoint automatically filters out texts shorter than 20 characters to prevent processing garbage data._

### Health Check

Returns the operational status of the API and confirms the ML model is loaded into memory.

*   URL `/health`
*   Method GET

**Response: 200 OK**

    {
      "status": "healthy",
      "model_loaded": true,
      "model": "Soft Voting Ensemble",
      "version": "1.0.0"
    }

* * *

Authentication & Security
-------------------------

Currently, the API does not require authentication keys for internal microservice communication.

If exposing this API to the public internet, it is highly recommended to place it behind an API Gateway (like AWS API Gateway, Cloudflare Workers, or Nginx) to handle rate limiting and API key validation.

The API includes `CORSMiddleware` configured to allow requests from frontend origins (like `localhost:5173` for local React development).

* * *

Response Schemas
----------------

### Fused Result Schema

Field

Type

Description

`final_verdict`

string

Final classification. One of: `"spam"`, `"suspicious"`, `"safe"`.

`final_confidence`

integer

Fused confidence percentage (`0` to `100`).

`strategy`

string

Which system drove the decision. One of: `"ml_primary"`, `"rules_primary_ml_uncertain"`, `"ml_primary_with_rule_override"`.

`override_reason`

string / null

If the rule engine vetoed the ML model, this explains why.

`meta.response_time_ms`

integer

Total time taken to run both ML and Rules in parallel.

### Rule Engine Feature Severity

The rule engine breaks down text analysis into 11 features. Each feature returns a severity tag:

Tag

Meaning

`high`

Strong spam indicator (e.g., Pharmaceutical words detected).

`medium`

Moderate spam indicator (e.g., Click-bait phrases).

`low`

Weak spam indicator (e.g., One instance of excessive caps).

`none`

No spam indicators (e.g., Passed contextual relevance check).

### Error Responses

All errors return a standard JSON format and appropriate HTTP status codes.

**400 Bad Request** (Empty input or invalid batch)

    { "detail": "Empty text provided" }

**500 Internal Server Error** (Model file missing or corruption)

    { "detail": "[Errno 2] No such file or directory: 'models/soft_ensemble.joblib'" }

* * *

Fusion Logic (How it works)
---------------------------

SpamLens does not blindly trust the AI model. It uses dynamic weighting based on confidence:

1.  **ML-Primary (Default):** If the ML model is confident (>50% confidence), the final score is calculated as `ML (65%) + Rules (35%)`.
2.  **Rules-Primary:** If the ML model is uncertain (<50%), the system leans on the rule engine: `ML (40%) + Rules (60%)`.
3.  **Rule Override:** If the ML model predicts "Ham" (Safe) but the rule engine detects a critical hard-fail (e.g., `pharma_keywords` scores ≥ 18), the system triggers an override. It bumps the ML confidence to 60%, forces a 50/50 weight split, and flags `override_reason` in the response so the frontend can explain to the user why the AI was vetoed.

**Classification Thresholds:**

*   `≥ 70%` → Classified as `"spam"`
*   `40% - 69%` → Classified as `"suspicious"`
*   `< 40%` → Classified as `"safe"`

* * *

Local Development Setup
-----------------------

**Prerequisites:** Python 3.11+ (3.11 recommended for pre-compiled ML library wheels), Pip

**1\. Clone the repository:**

    git clone https://github.com/MaximizeAy/spamlens-api.git
    cd spamlens-api

**2\. Create a virtual environment and install dependencies:**

    python -m venv venv
    source venv/bin/activate  # On Windows use: venv\Scripts\activate
    pip install -r requirements.txt

**3\. Ensure the model file is in place:**

Verify that `models/soft_ensemble.joblib` exists in the root directory.

**4\. Run the server:**

    uvicorn main:app --reload

The API will be available at `http://localhost:8000`. Interactive documentation is automatically generated at `http://localhost:8000/docs`.

* * *

Load Testing
------------

SpamLens includes a Locust configuration to test concurrent request handling and ensure the async thread pool doesn't deadlock.

1.  Ensure the server is running locally.
2.  Run Locust: `locust`
3.  Open `http://localhost:8080` in your browser, set the number of users, and start swarming. The test script randomly hits both `/analyze` and `/analyze/batch` to simulate realistic traffic.