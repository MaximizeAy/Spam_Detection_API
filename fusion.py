# fusion.py
from pydantic import BaseModel

# We don't need to redefine RuleAnalysis here, we just accept it as a type hint
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
    Fuses ML and Rule Engine results. 
    ML is the primary driver (0.0 to 1.0 scale).
    Rules act as a weighted 'nudge' based on their 0-100 confidence scale.
    """
    
    # ==========================================
    # 1. SETUP YOUR "TUNING KNOBS"
    # ==========================================
    ML_DOMINANCE_THRESHOLD = 0.75 # If ML is 75%+ confident, ignore rules completely
    MAX_RULE_BOOST = 0.15         # Maximum 15% shift allowed by the rule engine
    
    # ==========================================
    # 2. ESTABLISH THE ML BASELINE (0.0 to 1.0)
    # ==========================================
    if ml.prediction.lower() == "spam":
        ml_spam_score = ml.confidence
    else:
        ml_spam_score = 1.0 - ml.confidence

    final_score = ml_spam_score
    strategy = "ml_driven"
    override_reason = None

    # ==========================================
    # 3. APPLY RULES AS A WEIGHTED "NUDGE"
    # ==========================================
    
    # If ML is VERY confident, trust it entirely
    if ml.confidence >= ML_DOMINANCE_THRESHOLD:
        strategy = "ml_dominant"
        override_reason = f"ML confidence ({ml.confidence*100:.1f}%) exceeded threshold. Rules ignored."
        
    # If ML is unsure, let the rules nudge the score
    else:
        # Rule engine confidence is 0-100, convert it to a 0.0-1.0 weight
        rule_weight = rules.confidence / 100.0 
        
        if rules.classification == "spam":
            # Higher rule confidence = bigger boost towards spam
            boost = rule_weight * MAX_RULE_BOOST
            final_score += boost
            strategy = "rule_assisted_spam"
            override_reason = f"ML uncertain. Rules classified as spam ({rules.confidence}%), applied +{boost:.2f} boost."
            
        elif rules.classification == "safe":
            # Higher rule confidence = bigger boost towards safe
            penalty = rule_weight * MAX_RULE_BOOST
            final_score -= penalty
            strategy = "rule_assisted_safe"
            override_reason = f"ML uncertain. Rules classified as safe ({rules.confidence}%), applied -{penalty:.2f} penalty."
            
        elif rules.classification == "suspicious":
            # "Suspicious" nudges slightly towards spam, but at half strength
            sus_boost = (rule_weight * MAX_RULE_BOOST) * 0.5
            final_score += sus_boost
            strategy = "rule_assisted_suspicious"
            override_reason = f"ML uncertain. Rules flagged as suspicious ({rules.confidence}%), applied +{sus_boost:.2f} boost."

    # ==========================================
    # 4. FINAL CALCULATION
    # ==========================================
    final_score = max(0.0, min(1.0, final_score))
    
    if final_score >= 0.5:
        final_verdict = "spam"
        final_confidence = final_score
    else:
        final_verdict = "safe"
        final_confidence = 1.0 - final_score

    # ==========================================
    # 5. PREPARE PAYLOAD FOR REACT FRONTEND
    # ==========================================
    # We must manually convert the RuleAnalysis dataclass features into 
    # a list of dictionaries, otherwise FastAPI will throw a serialization error.
    rules_features_json = [
        {
            "id": f.id,
            "name": f.name,
            "desc": f.desc,
            "icon": f.icon,
            "score": f.score,
            "severity": f.severity,
            "type": f.type
        } for f in rules.features
    ]

    return FusedVerdict(
        final_verdict=final_verdict,
        final_confidence=round(final_confidence, 4),
        ml={
            "prediction": ml.prediction,
            "confidence_pct": f"{ml.confidence * 100:.1f}%",
            "features": ml.features,
        },
        rules={
            "verdict": rules.classification, # Map 'classification' to 'verdict' for the frontend
            "confidence": rules.confidence,   # Pass the 0-100 integer
            "features": rules_features_json   # Pass the detailed rule flags!
        },
        strategy=strategy,
        override_reason=override_reason
    )