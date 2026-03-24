from __future__ import annotations

import json
from datetime import datetime

from flask import current_app


def generate_user_pdf_report(*, user, profile, crop_items, fert_items, disease_items) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        from reportlab.lib import colors
    except Exception as exc:
        raise RuntimeError("reportlab is not installed. Install requirements-report.txt") from exc

    import io

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="AgroSmart Report")
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph("AgroSmart - User Report", styles["Title"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Profile", styles["Heading2"]))
    loc = (profile.location if profile else "") or "-"
    size = (profile.farm_size_acres if profile else None)
    story.append(Paragraph(f"Name: {user.name}", styles["Normal"]))
    story.append(Paragraph(f"Email: {user.email}", styles["Normal"]))
    story.append(Paragraph(f"Location: {loc}", styles["Normal"]))
    story.append(Paragraph(f"Farm size (acres): {size if size is not None else '-'}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Recent Crop Predictions", styles["Heading2"]))
    story.extend(_table_block(["Time", "Crop", "Season", "Confidence", "Model"], crop_items))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Recent Fertilizer Recommendations", styles["Heading2"]))
    story.extend(_table_block(["Time", "Crop", "Status", "Focus"], fert_items))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Recent Disease Predictions", styles["Heading2"]))
    story.extend(_table_block(["Time", "Disease", "Confidence", "Model"], disease_items))

    doc.build(story)
    return buf.getvalue()


def _table_block(headers: list[str], rows: list[list[str]]) -> list:
    from reportlab.platypus import Table, TableStyle, Spacer
    from reportlab.lib import colors

    if not rows:
        return [Spacer(1, 6)]

    data = [headers] + rows
    table = Table(data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#355f2e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cfd8c2")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f7f3ea")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return [table, Spacer(1, 6)]
