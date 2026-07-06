import pandas as pd
import re
import asyncio
import time
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from joblib import load

# Import the rule engine and fusion logic
from rule_engine import analyze_email
from fusion import fuse_verdicts, MLVerdict

# ====================================
#          Feature Extraction
# ====================================
SECURITY_KEYWORDS = [
    "otp", "verification", "verify", "secure", "security", 
    "password", "account", "login", "recover", "code", 
    "authenticate", "authentication", "2fa"
]
DELIVERY_KEYWORDS = ["parcel", "delivery", "shipment"]
PROMOTION_KEYWORDS = ["free", "win", "prize", "offer"]
URGENCY_WORDS = ["urgent", "immediately", "suspended", "restricted", "limited", "expire", "warning"]

def extract_subject(text):
    text = text.lower()
    if any(word in text for word in SECURITY_KEYWORDS): return "security"
    if any(word in text for word in DELIVERY_KEYWORDS): return "delivery"
    if any(word in text for word in PROMOTION_KEYWORDS): return "promotion"
    return "general"

def extract_url_features(text):
    urls = re.findall(r'https?://\S+|www\.\S+', text)
    return {
        "combined_text": text,
        "has_url": int(len(urls) > 0),
        "url_count": len(urls)
    }

def extract_security_features(text):
    text = text.lower()
    keyword_count = sum(keyword in text for keyword in SECURITY_KEYWORDS)
    return {"security_keyword_count": keyword_count}

def extract_urgency_features(text):
    text = text.lower()
    urgency_count = sum(word in text for word in URGENCY_WORDS)
    return {"urgency_count": urgency_count}

def extract_custom_features(text):
    features = {}
    features.update(extract_url_features(text))
    features.update(extract_security_features(text))
    features.update(extract_urgency_features(text))
    return features

def normalize_message(text: str) -> str:
    text = re.sub(r'[\r\n]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ====================================
#     Direct Model Inference Function
# ====================================
# Load model once at startup
model = load("models/soft_ensemble.joblib")

def run_model_inference(text: str) -> MLVerdict:
    """
    Directly calls the joblib model in memory.
    Used by BOTH /predict and /analyze so we never make HTTP calls to ourselves.
    """
    clean_message = normalize_message(text)
    sample = pd.DataFrame([extract_custom_features(clean_message)])

    start_time = time.perf_counter()
    prediction = model.predict(sample)
    confidence = model.predict_proba(sample).max()
    prediction_time_ms = (time.perf_counter() - start_time) * 1000
    
    label = "Spam" if prediction[0] == 1 else "Ham"

    return MLVerdict(
        prediction=label,
        confidence=round(float(confidence), 4),
        model="Soft Voting Ensemble",
        version="1.0.0",
        normalized_message=clean_message,
        message_length=len(clean_message),
        prediction_time_ms=round(prediction_time_ms, 2),
        features={
            "has_url": bool(sample.iloc[0]["has_url"]),
            "url_count": int(sample.iloc[0]["url_count"]),
            "security_keyword_count": int(sample.iloc[0]["security_keyword_count"]),
            "urgency_count": int(sample.iloc[0]["urgency_count"])
        }
    )


# ====================================
#          FastAPI App Setup
# ====================================
app = FastAPI(
    title="SpamLens Fusion API",
    description="Detects spam using a soft voting ensemble fused with a rule engine.",
    version="1.0.0"
)

# CORS: Required so the React frontend can talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite default
        "http://localhost:3000",   # CRA default
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(
    filename="logs/api.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)


# ====================================
#              Schemas
# ====================================
class EmailRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, value):
        if not value.strip():
            raise ValueError("Message cannot be empty.")
        return value

class BatchRequest(BaseModel):
    messages: list[str]

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, value):
        if not value:
            raise ValueError("At least one message is required.")
        cleaned = [m.strip() for m in value]
        if any(not m for m in cleaned):
            raise ValueError("Messages cannot be empty.")
        return cleaned

class AnalyzeRequest(BaseModel):
    text: str

class AnalyzeBatchRequest(BaseModel):
    texts: list[str]


# ====================================
#       Original Endpoints (Untouched)
# ====================================
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model_loaded": True,
        "model": "Soft Voting Ensemble",
        "version": "1.0.0"
    }

@app.get("/")
def home():
    return {"message": "Spam Detection API is running"}

@app.post("/predict")
def predict(email: EmailRequest):
    try:
        ml_result = run_model_inference(email.message)
        
        logging.info(
            f"Prediction={ml_result.prediction}, "
            f"Confidence={ml_result.confidence:.4f}, "
            f"Length={ml_result.message_length}, "
            f"Time={ml_result.prediction_time_ms:.2f}ms"
        )
        
        return {
            "prediction": ml_result.prediction,
            "confidence": ml_result.confidence,
            "model": ml_result.model,
            "version": ml_result.version,
            "normalized_message": ml_result.normalized_message,
            "message_length": ml_result.message_length,
            "prediction_time_ms": ml_result.prediction_time_ms,
            "features": ml_result.features
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict-batch")
def predict_batch(batch: BatchRequest):
    results = []
    for message in batch.messages:
        ml_result = run_model_inference(message)
        results.append({
            "message": message,
            "prediction": ml_result.prediction,
            "confidence": ml_result.confidence
        })
    return {"predictions": results}


# ====================================
#       New Fusion Endpoints
# ====================================
@app.post("/analyze")
async def analyze_single(req: AnalyzeRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty text provided")

    start = time.perf_counter()

    # Run ML and rules in parallel using background threads
    # (run_in_executor prevents CPU-bound model from blocking the async server)
    loop = asyncio.get_event_loop()
    ml_result, rules_result = await asyncio.gather(
        loop.run_in_executor(None, run_model_inference, req.text),
        loop.run_in_executor(None, analyze_email, req.text),
    )

    if rules_result is None:
        raise HTTPException(status_code=400, detail="Rule engine returned no result")

    fused = fuse_verdicts(ml_result, rules_result)
    elapsed_ms = round((time.perf_counter() - start) * 1000)

    return {
        "final_verdict": fused.final_verdict,
        "final_confidence": fused.final_confidence,
        "ml": fused.ml,
        "rules": fused.rules,
        "strategy": fused.strategy,
        "override_reason": fused.override_reason,
        "meta": {"response_time_ms": elapsed_ms},
    }


@app.post("/analyze/batch")
async def analyze_batch(req: AnalyzeBatchRequest):
    valid_texts = [t.strip() for t in req.texts if len(t.strip()) > 20]
    if not valid_texts:
        raise HTTPException(status_code=400, detail="No valid texts provided")

    start = time.perf_counter()
    loop = asyncio.get_event_loop()

    tasks = []
    for text in valid_texts:
        tasks.append(loop.run_in_executor(None, run_model_inference, text))
        tasks.append(loop.run_in_executor(None, analyze_email, text))

    results_raw = await asyncio.gather(*tasks, return_exceptions=True)

    batch = []
    for i in range(0, len(results_raw), 2):
        ml_res = results_raw[i]
        rules_res = results_raw[i + 1]

        if isinstance(ml_res, Exception) or isinstance(rules_res, Exception):
            continue
        if rules_res is None:
            continue

        fused = fuse_verdicts(ml_res, rules_res)
        batch.append({
            "text": valid_texts[i // 2],
            "final_verdict": fused.final_verdict,
            "final_confidence": fused.final_confidence,
            "ml": {
                "prediction": fused.ml["prediction"],
                "confidence_pct": fused.ml["confidence_pct"],
                "features": fused.ml["features"],
            },
            "rules": {
                "verdict": fused.rules["verdict"],
                "confidence": fused.rules["confidence"],
            },
            "strategy": fused.strategy,
        })

    elapsed_ms = round((time.perf_counter() - start) * 1000)

    spam_count = sum(1 for b in batch if b["final_verdict"] == "spam")
    safe_count = sum(1 for b in batch if b["final_verdict"] == "safe")
    sus_count = sum(1 for b in batch if b["final_verdict"] == "suspicious")

    return {
        "total": len(batch),
        "spam": spam_count,
        "suspicious": sus_count,
        "safe": safe_count,
        "results": batch,
        "meta": {"response_time_ms": elapsed_ms},
    }