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

Currently, the API does not require authentication keys for internal microservice communication, and the backend is hosted on a "FREE" Render instance and may take a short time to wake up after periods of inactivity.

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