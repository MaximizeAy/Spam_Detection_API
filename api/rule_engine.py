# rule_engine.py
"""SpamLens Rule Engine — Python port for FastAPI integration."""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FeatureResult:
    id: str
    name: str
    desc: str
    icon: str
    score: float
    severity: str  # none, low, medium, high
    type: str      # flag, clear, warn


@dataclass
class RuleAnalysis:
    confidence: int
    classification: str  # spam, suspicious, safe
    features: list[FeatureResult]
    text: str


def _check_excessive_caps(text: str) -> dict:
    caps = len(re.findall(r'[A-Z]{3,}', text))
    return {"score": min(caps * 6, 30), "detail": f"{caps} all-caps segments"}


def _check_suspicious_urls(text: str) -> dict:
    urls = re.findall(r'https?://[^\s]+', text)
    suspicious = 0
    sus_words = ['free', 'cheap', 'deal', 'offer', 'claim', 'win',
                 'bonus', 'click', 'xyz', '.biz', '.tk', '.top']
    for u in urls:
        if any(w in u.lower() for w in sus_words):
            suspicious += 1
    if len(urls) > 3:
        suspicious += 2
    return {"score": suspicious * 10, "detail": f"{suspicious}/{len(urls)} URLs flagged"}


def _check_excessive_punctuation(text: str) -> dict:
    excl = len(re.findall(r'!{2,}', text))
    ques = len(re.findall(r'\?{2,}', text))
    return {"score": (excl + ques) * 5,
            "detail": f"{excl} exclamation bursts, {ques} question bursts"}


def _check_greeting_quality(text: str) -> dict:
    bad = ['dear friend', 'dear beloved', 'dear customer', 'dear user',
           'dear member', 'attention:', 'hello dear']
    lower = text.lower()
    found = [g for g in bad if g in lower]
    has_personal = bool(re.search(r'\b(hi|hey|hello)\s+[A-Z][a-z]+\b', text))
    if found:
        return {"score": len(found) * 8, "detail": f'"{found[0]}" detected'}
    elif has_personal:
        return {"score": 0, "detail": "Personalized greeting"}
    return {"score": 0, "detail": "No greeting detected"}


def _check_personalization(text: str) -> dict:
    signals = [
        re.compile(r'\b(yesterday|tomorrow|last week|next week)\b', re.I),
        re.compile(r'\b(meeting|call|lunch|coffee|standup)\b', re.I),
        re.compile(r'\b(attachment|attached|document|file)\b', re.I),
        re.compile(r'\b(please review|please check|could you|would you)\b', re.I),
        re.compile(r'\b(project|task|deadline|milestone)\b', re.I),
    ]
    hits = sum(1 for s in signals if s.search(text))
    return {"score": -hits * 6, "detail": f"{hits} contextual signals found"}


def _check_structure_quality(text: str) -> dict:
    sentences = [s for s in re.split(r'[.!?]+', text) if len(s.strip()) > 10]
    avg_len = (sum(len(s.strip().split()) for s in sentences) / len(sentences)) if sentences else 0
    paragraphs = len([p for p in re.split(r'\n\n+', text) if len(p.strip()) > 20])
    score = 0
    if 5 < avg_len < 25:
        score -= 5
    if paragraphs >= 2:
        score -= 4
    if len(sentences) >= 3:
        score -= 3
    return {"score": score,
            "detail": f"{len(sentences)} sentences, avg {round(avg_len)} words, {paragraphs} paragraphs"}


# ── Rule definitions ──
RULES = [
    {
        "id": "urgency_words",
        "name": "Urgency Triggers",
        "desc": "Words designed to create false urgency",
        "icon": "fa-solid fa-bolt",
        "patterns": [re.compile(p, re.I) for p in [
            r'urgent', r'act now', r'immediate', r'hurry', r'limited time',
            r"don't miss", r'before it', r'asap', r'respond now'
        ]],
        "weight": 12,
        "type": "flag",
        "check": None,
    },
    {
        "id": "excessive_caps",
        "name": "Excessive Caps Lock",
        "desc": "Overuse of uppercase for attention",
        "icon": "fa-solid fa-font",
        "patterns": None,
        "weight": 6,
        "type": "flag",
        "check": _check_excessive_caps,
    },
    {
        "id": "money_mentions",
        "name": "Money / Financial Bait",
        "desc": "Unsolicited money-related promises",
        "icon": "fa-solid fa-dollar-sign",
        "patterns": [re.compile(p, re.I) for p in [
            r'\$\d[\d,]*\d', r'million', r'inheritance', r'transfer.*account',
            r'free money', r'earn.*\$', r'profit', r'investment.*guarantee'
        ]],
        "weight": 14,
        "type": "flag",
        "check": None,
    },
    {
        "id": "suspicious_urls",
        "name": "Suspicious URLs",
        "desc": "Untrustworthy or obfuscated links",
        "icon": "fa-solid fa-link",
        "patterns": None,
        "weight": 15,
        "type": "flag",
        "check": _check_suspicious_urls,
    },
    {
        "id": "excessive_punctuation",
        "name": "Excessive Punctuation",
        "desc": "Multiple exclamation marks or question marks",
        "icon": "fa-solid fa-exclamation",
        "patterns": None,
        "weight": 5,
        "type": "flag",
        "check": _check_excessive_punctuation,
    },
    {
        "id": "pharma_keywords",
        "name": "Pharmaceutical Keywords",
        "desc": "Drug names or pharmacy-related spam",
        "icon": "fa-solid fa-pills",
        "patterns": [re.compile(p, re.I) for p in [
            r'viagra', r'cialis', r'xanax', r'valium', r'no prescription',
            r'medication', r'pharmacy', r'diet pill', r'weight loss.*guarantee'
        ]],
        "weight": 18,
        "type": "flag",
        "check": None,
    },
    {
        "id": "click_bait",
        "name": "Click-Bait Phrases",
        "desc": "Manipulative phrases to drive clicks",
        "icon": "fa-solid fa-arrow-pointer",
        "patterns": [re.compile(p, re.I) for p in [
            r'click here', r'click now', r'sign up now', r'subscribe now',
            r'open now', r'verify.*account', r'confirm.*details', r'update.*information'
        ]],
        "weight": 10,
        "type": "flag",
        "check": None,
    },
    {
        "id": "greeting_quality",
        "name": "Greeting Quality",
        "desc": "Generic or impersonal salutations",
        "icon": "fa-solid fa-hand",
        "patterns": None,
        "weight": 8,
        "type": "warn",
        "check": _check_greeting_quality,
    },
    {
        "id": "sender_impersonation",
        "name": "Impersonation Signals",
        "desc": "Claims of authority or fake identity",
        "icon": "fa-solid fa-user-secret",
        "patterns": [re.compile(p, re.I) for p in [
            r'prince', r'king', r'minister', r'ceo.*need', r'bank.*manager',
            r'fbi', r'irs', r'government', r'official.*notice', r'account.*suspended'
        ]],
        "weight": 16,
        "type": "flag",
        "check": None,
    },
    {
        "id": "personalization",
        "name": "Contextual Relevance",
        "desc": "Evidence of genuine, specific context",
        "icon": "fa-solid fa-message",
        "patterns": None,
        "weight": 6,
        "type": "clear",
        "check": _check_personalization,
    },
    {
        "id": "structure_quality",
        "name": "Writing Structure",
        "desc": "Sentence variety and paragraph formatting",
        "icon": "fa-solid fa-paragraph",
        "patterns": None,
        "weight": 4,
        "type": "clear",
        "check": _check_structure_quality,
    },
]


def analyze_email(text: str) -> Optional[RuleAnalysis]:
    """Run the full rule engine against a text. Returns None if text is empty."""
    text = text.strip()
    if not text:
        return None

    features: list[FeatureResult] = []
    total_score = 0.0

    for rule in RULES:
        if rule["check"]:
            result = rule["check"](text)
        elif rule["patterns"]:
            matches = [p for p in rule["patterns"] if p.search(text)]
            result = {
                "score": len(matches) * rule["weight"],
                "detail": f"{len(matches)} pattern(s) matched" if matches else "No matches"
            }
        else:
            continue

        clamped = max(-20, min(35, result["score"]))
        total_score += clamped

        raw_pct = abs(clamped) / 35 * 100
        if clamped <= 0:
            severity = "none"
        elif raw_pct < 30:
            severity = "low"
        elif raw_pct < 65:
            severity = "medium"
        else:
            severity = "high"

        features.append(FeatureResult(
            id=rule["id"],
            name=rule["name"],
            desc=result["detail"],
            icon=rule["icon"],
            score=clamped,
            severity=severity,
            type=rule["type"],
        ))

    confidence = round(max(0, min(100, (total_score + 40) / 160 * 100)))

    if confidence >= 70:
        classification = "spam"
    elif confidence >= 40:
        classification = "suspicious"
    else:
        classification = "safe"

    return RuleAnalysis(
        confidence=confidence,
        classification=classification,
        features=features,
        text=text,
    )