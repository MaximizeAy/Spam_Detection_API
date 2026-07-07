# Inside fusion.py
from pydantic import BaseModel
from rule_engine import RuleAnalysis 

class MLVerdict(BaseModel):
    prediction: str
    confidence: float
    features: dict

class FusedVerdict(BaseModel):
    final_verdict: str
    final_confidence: float
    ml: dict
    rules: dict
    strategy: str
    override_reason: str | None

def fuse_verdicts(ml: MLVerdict, rules: RuleAnalysis) -> FusedVerdict:
    """
    Fuses ML and Rule Engine into a single 0-100 percentage.
    ML and Rules ALWAYS sum together. ML just has a heavier weight.
    """
    
    # ==========================================
    # 1. NORMALIZE EVERYTHING TO 0 - 100 SCALE
    # ==========================================
    
    # ML model outputs 0.0 to 1.0. Convert to 0-100.
    if ml.prediction.lower() == "spam":
        ml_spam_score = ml.confidence * 100
    else:
        ml_spam_score = (1.0 - ml.confidence) * 100

    # Rule engine already outputs 0-100 (where 100 is definitely spam)
    rules_spam_score = rules.confidence 

    # ==========================================
    # 2. SET WEIGHTS (Who has more power?)
    # ==========================================
    # ML has 60% of the total power, Rules have 40%.
    # Change these if you want Rules to have more influence!
    ML_WEIGHT = 0.6
    RULES_WEIGHT = 0.4

    # ==========================================
    # 3. CALCULATE THE FUSED SCORE (ALWAYS SUMS BOTH)
    # ==========================================
    raw_fused_score = (ml_spam_score * ML_WEIGHT) + (rules_spam_score * RULES_WEIGHT)
    
    strategy = "fused_average"
    override_reason = f"Averaged ML ({ml_spam_score:.0f}%) and Rules ({rules_spam_score}%)"

    # Handle the "Suspicious" middle-ground from rules
    if rules.classification == "suspicious":
        # If rules are suspicious, pull the final score slightly towards the 50% middle line
        raw_fused_score = (raw_fused_score + 50) / 2 
        strategy = "fused_suspicious_nudge"
        override_reason = f"Rules flagged suspicious. Pulled score towards midpoint."

    # Clamp between 0 and 100 just in case
    final_score_100 = max(0, min(100, raw_fused_score))

    # ==========================================
    # 4. DETERMINE FINAL VERDICT & CONFIDENCE
    # ==========================================
    if final_score_100 >= 50:
        final_verdict = "spam"
        # Confidence is how far past 50% it is (e.g., 80% score = 80% spam risk)
        final_confidence = round(final_score_100, 1)
    else:
        final_verdict = "safe"
        # Confidence is how far below 50% it is (e.g., 20% score = 80% safe confidence)
        final_confidence = round(100 - final_score_100, 1)

    # ==========================================
    # 5. PREPARE PAYLOAD FOR REACT FRONTEND
    # ==========================================
    rules_features_json = [
        {
            "id": f.id, "name": f.name, "desc": f.desc, "icon": f.icon,
            "score": f.score, "severity": f.severity, "type": f.type
        } for f in rules.features
    ]

    return FusedVerdict(
        final_verdict=final_verdict,
        final_confidence=final_confidence, # Now guaranteed to be 0-100 (e.g., 84.5)
        ml={
            "prediction": ml.prediction,
            "confidence_pct": f"{ml.confidence * 100:.1f}%",
            "features": ml.features,
        },
        rules={
            "verdict": rules.classification,
            "confidence": rules.confidence,
            "features": rules_features_json
        },
        strategy=strategy,
        override_reason=override_reason
    )