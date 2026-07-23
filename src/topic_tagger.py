"""Optional keyword-based topic tagging (not required by the app, kept for reuse)."""

import re

TOPIC_KEYWORDS = {
    "Devices & Enrollment": ["intune", "enroll", "autopilot", "device", "provisioning", "mdm"],
    "Apps": ["app", "win32", "deploy application", "office", "package"],
    "Compliance": ["compliance", "policy", "bitlocker", "jailbreak", "conditional access"],
    "Updates": ["update", "windows update", "delivery optimization", "feature update", "ring"],
    "Security": ["defender", "firewall", "antivirus", "attack surface", "edr"],
    "Identity": ["azure ad", "entra", "role", "group", "authentication"],
}


def detect_topic(text):
    if not text:
        return "General"
    lowered = text.lower()
    scores = {}
    for topic, kws in TOPIC_KEYWORDS.items():
        s = sum(len(re.findall(re.escape(k), lowered)) for k in kws)
        if s:
            scores[topic] = s
    return max(scores, key=scores.get) if scores else "General"


def tag_questions(questions):
    for q in questions:
        combined = q.get("question_text", "") + " " + " ".join(q.get("options", {}).values())
        q["keyword_topic"] = detect_topic(combined)
    return questions


def get_available_topics(questions):
    return sorted({q.get("topic", "General") for q in questions})
