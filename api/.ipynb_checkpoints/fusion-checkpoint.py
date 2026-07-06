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


def fuse_verdicts(ml: MLVerdict, rules: RuleAnalysis) -> FusedResult:

    ml_internal_class = _ml_label_to_internal(ml.prediction)
    ml_confidence_pct = round(ml.confidence * 100)

    # ── Step 1: Rule-based override check ──
    # If ML says "Ham" but rules found a hard spam signal, override
    override_reason = None
    if ml_internal_class == "safe":
        for feat in rules.features:
            if feat.id in HARD_SPAM_TRIGGERS and feat.score >= HARD_SPAM_SCORE_THRESHOLD:
                override_reason = (
                    f"Rule override: '{feat.name}' scored {feat.score} "
                    f"but model predicted '{ml.prediction}' at {ml_confidence_pct}%"
                )
                # Bump ML side to at least 60 so the fusion math doesn't drown it
                ml_confidence_pct = max(ml_confidence_pct, 60)
                ml_internal_class = "suspicious"
                break

    # ── Step 2: Dynamic weight selection ──
    if override_reason:
        # Override triggered — split evenly, rules already influenced ML side
        ml_weight, rule_weight, strategy = 0.50, 0.50, "ml_primary_with_rule_override"
    elif ml_confidence_pct < 50:
        # ML is uncertain or says safe — lean on rules
        ml_weight, rule_weight, strategy = 0.40, 0.60, "rules_primary_ml_uncertain"
    else:
        # ML is confident — trust it, use rules for context
        ml_weight, rule_weight, strategy = 0.65, 0.35, "ml_primary"

    # ── Step 3: Weighted fusion ──
    fused = round(ml_confidence_pct * ml_weight + rules.confidence * rule_weight)
    fused = max(0, min(100, fused))

    if fused >= 70:
        final_verdict = "spam"
    elif fused >= 40:
        final_verdict = "suspicious"
    else:
        final_verdict = "safe"

    # ── Step 4: Build response ──
    return FusedResult(
        final_verdict=final_verdict,
        final_confidence=fused,
        ml={
            "prediction": ml.prediction,
            "internal_class": ml_internal_class,
            "confidence_pct": ml_confidence_pct,
            "confidence_raw": round(ml.confidence, 4),
            "model": ml.model,
            "version": ml.version,
            "prediction_time_ms": ml.prediction_time_ms,
            "features": ml.features,
        },
        rules={
            "verdict": rules.classification,
            "confidence": rules.confidence,
            "features": [
                {
                    "id": f.id,
                    "name": f.name,
                    "desc": f.desc,
                    "icon": f.icon,
                    "score": f.score,
                    "severity": f.severity,
                    "type": f.type,
                }
                for f in rules.features
            ],
        },
        strategy=strategy,
        override_reason=override_reason,
    )