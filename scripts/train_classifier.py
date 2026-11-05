from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Config
from app.core.classifiers.ml import MLClassifier


def main() -> None:
    classifier = MLClassifier.train_default(seed=7)
    output = Path(Config.MODEL_DIR) / "classifier.joblib"
    classifier.save(output)
    print(
        f"Trained on {classifier.metadata['samples']} samples across "
        f"{len(classifier.classes)} categories"
    )
    print(f"Saved model to {output}")


if __name__ == "__main__":
    main()
