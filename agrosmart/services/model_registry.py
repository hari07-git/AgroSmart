from __future__ import annotations

from pathlib import Path

from flask import current_app

from ..models import ModelArtifact


def get_active_model(kind: str) -> dict | None:
    row = ModelArtifact.query.filter_by(kind=kind, active=True).order_by(ModelArtifact.uploaded_at.desc()).first()
    if not row:
        return None

    base = Path(current_app.config["MODEL_STORE"])
    path = base / row.filename
    labels_path = base / row.labels_filename if row.labels_filename else None
    return {
        "id": row.id,
        "kind": row.kind,
        "version": row.version,
        "path": path,
        "labels_path": labels_path,
    }
