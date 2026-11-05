from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .ml import MLClassifier
from .rules import RuleEngine


@dataclass
class Classification:
    category: str
    source: str
    confidence: float
    rule_id: str | None = None
    needs_review: bool = False


class ClassificationEngine:
    def __init__(self, rules_path: Path, model_path: Path, categories_path: Path):
        self.rules = RuleEngine.from_file(Path(rules_path))
        self.ml = MLClassifier.load_or_train(Path(model_path))
        with open(categories_path, encoding="utf-8") as handle:
            payload = json.load(handle)
        self.categories = payload["categories"]
        self.category_names = {category["name"] for category in self.categories}

    def classify(self, description: str, direction: str | None = None) -> Classification:
        rule = self.rules.classify(description, direction)
        if rule and rule.confidence >= 0.88:
            return Classification(
                category=rule.category,
                source="rule",
                confidence=rule.confidence,
                rule_id=rule.rule_id,
            )

        ml_result = self.ml.predict(description, direction)
        if ml_result and ml_result[1] >= 0.42:
            category, probability = ml_result
            if category in self.category_names:
                return Classification(
                    category=category,
                    source="ml",
                    confidence=round(probability, 4),
                    needs_review=probability < 0.6,
                )

        if rule:
            return Classification(
                category=rule.category,
                source="rule",
                confidence=rule.confidence,
                rule_id=rule.rule_id,
                needs_review=rule.confidence < 0.75,
            )

        return Classification(
            category="Uncategorized",
            source="fallback",
            confidence=0.0,
            needs_review=True,
        )
