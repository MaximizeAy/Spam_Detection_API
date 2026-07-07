# fusion.py
"""Score fusion adapted to the actual ensemble model output schema."""

from dataclasses import dataclass
from rule_engine import RuleAnalysis


@dataclass
class MLVerdict:
    prediction: str          # "Spam", "Ham", etc.
    confidence: float        # 0.0 – 1.0
    model: str               # "Soft Voting Ensemble"
    version: str             # "1.0.0"
    normalized_message: str
    message_length: int
    prediction_time_ms: float
    features: dict           # { has_url, url_count, security_keyword_count, urgency_count }


@dataclass
class FusedResult:
    final_verdict: str
    final_confidence: int
    ml: dict
    rules: dict
    strategy: str
    override_reason: str | None


# ── Hard-signal rules that can veto a "Ham" prediction ──
HARD_SPAM_TRIGGERS = {"pharma_keywords", "sender_impersonation"}
HARD_SPAM_SCORE_THRESHOLD = 18


def _ml_label_to_internal(prediction: str) -> str:
    p = prediction.lower().strip()
    if p in ("spam", "phishing", "fraud"):
        return "spam"
    if p in ("suspicious", "review"):
        return "suspicious"
    # "Ham", "Safe", "Not Spam", etc.
    return "safe"


# Inside fusion.py
from pydantic import BaseModel

# Make sure these match your actual data structures
class MLVerdict(BaseModel):
    prediction: str
    confidence: float
    features: dict

class RulesVerdict(BaseModel):
    verdict: str
    confidence: float

class FusedVerdict(BaseModel):
    final_verdict: str
    final_confidence: float
    ml: dict
    rules: dict
    strategy: str
    override_reason: str | None

def fuse_verdicts(ml: MLVerdict, rules: RulesVerdict) -> FusedVerdict:
    """
    Fuses ML and Rule Engine results. 
    ML is the primary driver. Rules act as a 'nudge' rather than a hard override.
    """
    
    # ==========================================
    # 1. SETUP YOUR "TUNING KNOBS" HERE
    # ==========================================
    # How much should rules push the ML score? 
    # Keep these numbers LOW (0.05 to 0.15) so ML stays in control.
    RULE_SPAM_BOOST = 0.10    # If rules say spam, add 10% to ML confidence
    RULE_SAFE_BOOST = 0.10    # If rules say safe, add 10% to ML safe confidence
    ML_DOMINANCE_THRESHOLD = 0.75 # If ML is this confident, IGNORE rules completely
    
    # ==========================================
    # 2. ESTABLISH THE ML BASELINE
    # ==========================================
    # Convert ML prediction into a 0.0 to 1.0 "spam score"
    if ml.prediction.lower() == "spam":
        ml_spam_score = ml.confidence
    else:
        ml_spam_score = 1.0 - ml.confidence

    final_score = ml_spam_score
    strategy = "ml_driven"
    override_reason = None

    # ==========================================
    # 3. APPLY RULES AS A "NUDGE" (Not an override)
    # ==========================================
    
    # Scenario A: ML is VERY confident. Trust the ML model entirely.
    if ml.confidence >= ML_DOMINANCE_THRESHOLD:
        strategy = "ml_dominant"
        override_reason = f"ML confidence ({ml.confidence:.2f}) exceeded threshold. Rules ignored."
        
    # Scenario B: ML is unsure. Let the rules nudge the score.
    else:
        if rules.verdict.lower() == "spam":
            final_score += RULE_SPAM_BOOST
            strategy = "rule_assisted_spam"
            override_reason = f"ML uncertain. Rules detected spam, applied +{RULE_SPAM_BOOST} boost."
            
        elif rules.verdict.lower() == "safe":
            final_score -= RULE_SAFE_BOOST
            strategy = "rule_assisted_safe"
            override_reason = f"ML uncertain. Rules detected safe, applied -{RULE_SAFE_BOOST} penalty."

    # ==========================================
    # 4. FINAL CALCULATION
    # ==========================================
    # Clamp the score between 0.0 and 1.0 just in case
    final_score = max(0.0, min(1.0, final_score))
    
    # 0.5 is the middle threshold. Above 0.5 = Spam, Below 0.5 = Safe
    if final_score >= 0.5:
        final_verdict = "spam"
        final_confidence = final_score
    else:
        final_verdict = "safe"
        final_confidence = 1.0 - final_score # Flip confidence for "safe"

    return FusedVerdict(
        final_verdict=final_verdict,
        final_confidence=round(final_confidence, 4),
        ml={
            "prediction": ml.prediction,
            "confidence_pct": f"{ml.confidence * 100:.1f}%",
            "features": ml.features,
        },
        rules={
            "verdict": rules.verdict,
            "confidence": rules.confidence,
        },
        strategy=strategy,
        override_reason=override_reason
    )