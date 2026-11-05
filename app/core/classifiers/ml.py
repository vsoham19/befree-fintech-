from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion

from .merchants import iter_training_examples


class MLClassifier:
    def __init__(self, vectorizer=None, model=None, classes=None, metadata=None):
        self.vectorizer: FeatureUnion | None = vectorizer
        self.model: LogisticRegression | None = model
        self.classes: list[str] = classes or []
        self.metadata: dict = metadata or {}

    @staticmethod
    def _features(description: str, direction: str | None) -> str:
        return f"{direction or 'unknown'} {description}"

    @classmethod
    def train_default(cls, seed: int = 7) -> "MLClassifier":
        texts: list[str] = []
        labels: list[str] = []
        for description, direction, category in iter_training_examples(seed=seed):
            texts.append(cls._features(description, direction))
            labels.append(category)

        vectorizer = FeatureUnion(
            [
                (
                    "word",
                    TfidfVectorizer(
                        lowercase=True,
                        ngram_range=(1, 2),
                        token_pattern=r"(?u)\b\w+\b",
                        sublinear_tf=True,
                    ),
                ),
                (
                    "char",
                    TfidfVectorizer(
                        lowercase=True,
                        analyzer="char_wb",
                        ngram_range=(2, 5),
                        sublinear_tf=True,
                        min_df=2,
                    ),
                ),
            ]
        )
        matrix = vectorizer.fit_transform(texts)
        model = LogisticRegression(
            max_iter=4000,
            C=6.0,
            class_weight="balanced",
            random_state=seed,
        )
        model.fit(matrix, labels)

        return cls(
            vectorizer=vectorizer,
            model=model,
            classes=list(model.classes_),
            metadata={
                "version": 1,
                "samples": len(texts),
                "trained_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    @classmethod
    def load_or_train(cls, path: Path, seed: int = 7) -> "MLClassifier":
        path = Path(path)
        if path.exists():
            try:
                return cls.load(path)
            except Exception:
                pass
        classifier = cls.train_default(seed=seed)
        classifier.save(path)
        return classifier

    @classmethod
    def load(cls, path: Path) -> "MLClassifier":
        artifact = joblib.load(path)
        return cls(
            vectorizer=artifact["vectorizer"],
            model=artifact["model"],
            classes=list(artifact["classes"]),
            metadata=artifact.get("metadata", {}),
        )

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "vectorizer": self.vectorizer,
                "model": self.model,
                "classes": self.classes,
                "metadata": self.metadata,
            },
            path,
        )

    def predict(self, description: str, direction: str | None = None) -> tuple[str, float] | None:
        if self.vectorizer is None or self.model is None:
            return None
        matrix = self.vectorizer.transform([self._features(description, direction)])
        if matrix.nnz == 0:
            return None
        probabilities = self.model.predict_proba(matrix)[0]
        index = int(probabilities.argmax())
        return self.classes[index], float(probabilities[index])
