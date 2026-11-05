from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from .generator import PROFILES, convert_to_image_pdf, generate_statement


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic bank statement PDFs.")
    parser.add_argument("--count", type=int, default=12, help="Number of statements to generate")
    parser.add_argument("--out", default="data/samples", help="Output directory")
    parser.add_argument("--banks", default="hdfc,icici,sbi", help="Comma separated bank profiles")
    parser.add_argument("--image-ratio", type=float, default=0.35, help="Share of scanned PDFs")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--months", type=int, default=3, help="Months covered per statement")
    parser.add_argument("--density", type=float, default=1.0, help="Transaction density multiplier")
    parser.add_argument("--dpi", type=int, default=300, help="Raster DPI for image PDFs")
    parser.add_argument("--clean", action="store_true", help="Remove previous generated samples")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    banks = [name.strip().lower() for name in args.banks.split(",") if name.strip()]
    unknown = [name for name in banks if name not in PROFILES]
    if unknown:
        parser.error(f"Unknown bank profile(s): {', '.join(unknown)}")
    if not banks:
        parser.error("At least one bank profile is required")

    if args.clean:
        for pattern in ("*.pdf", "labels.json"):
            for path in out_dir.glob(pattern):
                path.unlink()

    rng = random.Random(args.seed)
    labels = []

    for index in range(args.count):
        bank = banks[index % len(banks)]
        as_image = rng.random() < args.image_ratio
        stem = f"{bank}_{'image' if as_image else 'text'}_{index + 1:03d}"
        target = out_dir / f"{stem}.pdf"

        if as_image:
            temp = out_dir / f"{stem}_source.pdf"
            label = generate_statement(
                temp, bank, rng, months=args.months, density=args.density
            )
            convert_to_image_pdf(temp, target, dpi=args.dpi)
            temp.unlink(missing_ok=True)
            label["pdf_type"] = "image"
            label["file"] = target.name
        else:
            label = generate_statement(
                target, bank, rng, months=args.months, density=args.density
            )

        labels.append(label)
        print(
            f"[{index + 1}/{args.count}] {target.name}: "
            f"{len(label['transactions'])} transactions ({label['pdf_type']})"
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "seed": args.seed,
        "samples": labels,
    }
    (out_dir / "labels.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(labels)} statements and labels.json to {out_dir}")


if __name__ == "__main__":
    main()
