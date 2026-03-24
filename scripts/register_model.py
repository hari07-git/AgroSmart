from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from uuid import uuid4


def main() -> int:
    parser = argparse.ArgumentParser(description="Register a model artifact in the DB and optionally activate it.")
    parser.add_argument("--kind", required=True, choices=["crop", "disease"])
    parser.add_argument("--version", required=True, help="Version label (e.g., v1, 2026-03-14)")
    parser.add_argument("--file", required=True, help="Path to model file (.joblib or .keras)")
    parser.add_argument("--labels", default="", help="Optional labels json path (disease only)")
    parser.add_argument("--activate", action="store_true", help="Make this model active for its kind")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from agrosmart import create_app
    from agrosmart.db import db
    from agrosmart.models import ModelArtifact

    src = Path(args.file).resolve()
    if not src.exists():
        raise SystemExit("Model file not found.")

    labels_src = Path(args.labels).resolve() if args.labels else None
    if labels_src and not labels_src.exists():
        raise SystemExit("Labels file not found.")

    app = create_app()
    with app.app_context():
        store = Path(app.config["MODEL_STORE"])
        store.mkdir(parents=True, exist_ok=True)

        final_name = f"{args.kind}_{args.version}_{uuid4().hex}_{src.name}"
        shutil.copy2(src, store / final_name)

        labels_final = None
        if labels_src:
            labels_final = f"{args.kind}_{args.version}_{uuid4().hex}_{labels_src.name}"
            shutil.copy2(labels_src, store / labels_final)

        row = ModelArtifact(
            kind=args.kind,
            version=args.version,
            filename=final_name,
            labels_filename=labels_final,
            active=False,
        )
        db.session.add(row)
        db.session.flush()

        if args.activate:
            ModelArtifact.query.filter_by(kind=args.kind, active=True).update({"active": False})
            row.active = True

        db.session.commit()
        print(f"Registered model id={row.id} kind={row.kind} version={row.version} active={row.active}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
