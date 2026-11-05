from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuleMatch:
    category: str
    confidence: float
    rule_id: str
    pattern: str


@dataclass
class Rule:
    id: str
    category: str
    direction: str
    confidence: float
    patterns: list[re.Pattern]


class RuleEngine:
    def __init__(self, rules: list[Rule]):
        self.rules = rules

    @classmethod
    def from_file(cls, path: Path) -> "RuleEngine":
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
        rules = []
        for item in payload.get("rules", []):
            patterns = [re.compile(pattern, re.IGNORECASE) for pattern in item.get("patterns", [])]
            rules.append(
                Rule(
                    id=item["id"],
                    category=item["category"],
                    direction=item.get("direction", "any").lower(),
                    confidence=float(item.get("confidence", 0.7)),
                    patterns=patterns,
                )
            )
        return cls(rules)

    def classify(self, description: str, direction: str | None = None) -> RuleMatch | None:
        text = description or ""
        best: tuple[float, Rule, str] | None = None

        for rule in self.rules:
            effective = rule.confidence
            if rule.direction != "any":
                if direction and direction != rule.direction:
                    continue
                if not direction:
                    effective *= 0.85
            for pattern in rule.patterns:
                if pattern.search(text):
                    if best is None or effective > best[0]:
                        best = (effective, rule, pattern.pattern)
                    break

        if best is None:
            return None
        confidence, rule, pattern = best
        return RuleMatch(
            category=rule.category,
            confidence=round(confidence, 4),
            rule_id=rule.id,
            pattern=pattern,
        )
