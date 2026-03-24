from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate heuristic disease classifier on a folder dataset.")
    parser.add_argument("--data_dir", required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    import sys

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from agrosmart.services.disease_features import heuristic_classify

    data_dir = Path(args.data_dir)
    total = 0
    correct = 0
    per = {}

    for class_dir in sorted([p for p in data_dir.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        label = class_dir.name
        for img in class_dir.rglob("*"):
            if img.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            total += 1
            pred = heuristic_classify(img).get("label")
            ok = (pred == label)
            correct += 1 if ok else 0
            per.setdefault(label, {"t": 0, "c": 0})
            per[label]["t"] += 1
            per[label]["c"] += 1 if ok else 0

    print(f"Total: {total}  Correct: {correct}  Acc: {correct/total if total else 0:.3f}")
    for k, v in per.items():
        acc = (v["c"] / v["t"]) if v["t"] else 0.0
        print(f"{k}: {v['c']}/{v['t']}  acc={acc:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
