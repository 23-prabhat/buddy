from __future__ import annotations

import re
from dataclasses import dataclass


QUESTION_WORDS = (
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "which",
    "whose",
    "whom",
    "can",
    "could",
    "would",
    "should",
    "is",
    "are",
    "do",
    "does",
    "did",
    "will",
    "have",
    "has",
)

REQUEST_PATTERNS = [
    r"\bexplain\b",
    r"\bwalk us through\b",
    r"\btell me\b",
    r"\btell us\b",
    r"\bdescribe\b",
    r"\bclarify\b",
    r"\bjustify\b",
    r"\bcan you\b",
    r"\bcould you\b",
    r"\bwould you\b",
    r"\bwhat about\b",
    r"\bhow come\b",
    r"\bany thoughts\b",
    r"\byour thoughts\b",
    r"\bwhat do you think\b",
    r"\bwhy did you\b",
    r"\bwhy do you\b",
    r"\bwhy was\b",
    r"\bhelp me understand\b",
]

USER_DIRECTED = [
    r"\byou\b",
    r"\byour\b",
    r"\byours\b",
    r"\bprabhat\b",  # optional personalization later
]


@dataclass
class QuestionDetection:
    is_question: bool
    directed_at_user: bool
    confidence: float
    reason: str
    normalized: str


class QuestionDetector:
    """Lightweight heuristic detector — no LLM required for MVP gate."""

    def detect(self, text: str, speaker: str | None = None) -> QuestionDetection:
        raw = (text or "").strip()
        normalized = re.sub(r"\s+", " ", raw)
        lower = normalized.lower().rstrip()

        if not lower or len(lower) < 3:
            return QuestionDetection(False, False, 0.0, "empty", normalized)

        # Don't treat user's own speech as a question to answer
        if speaker and speaker.lower() == "user":
            return QuestionDetection(False, False, 0.0, "user_speech", normalized)

        score = 0.0
        reasons: list[str] = []

        if "?" in normalized:
            score += 0.55
            reasons.append("question_mark")

        first = re.sub(r"^[^a-z]+", "", lower)
        for w in QUESTION_WORDS:
            if first.startswith(w + " ") or first == w:
                score += 0.35
                reasons.append(f"starts_{w}")
                break

        for pat in REQUEST_PATTERNS:
            if re.search(pat, lower):
                score += 0.4
                reasons.append(f"pattern:{pat}")
                break

        directed = False
        for pat in USER_DIRECTED:
            if re.search(pat, lower):
                directed = True
                score += 0.15
                reasons.append("user_ref")
                break

        # Imperative requests without ?
        if re.search(r"^(please\s+)?(explain|describe|clarify|justify)\b", lower):
            score += 0.35
            reasons.append("imperative_request")
            directed = True

        is_q = score >= 0.45
        # If clearly a question but no explicit you — still likely directed in 1:1 meetings
        if is_q and not directed:
            # default: treat external questions as likely directed at user in meeting mode
            directed = True
            reasons.append("default_directed")
            score = min(1.0, score + 0.1)

        conf = min(1.0, score)
        return QuestionDetection(
            is_question=is_q,
            directed_at_user=directed and is_q,
            confidence=conf,
            reason=",".join(reasons) or "none",
            normalized=normalized,
        )
