from __future__ import annotations

from .advisory import CROP_PROFILES


def fertilizer_recommendation(
    *,
    crop_name: str,
    nitrogen: float,
    phosphorus: float,
    potassium: float,
) -> dict:
    profile = next((p for p in CROP_PROFILES if p.name.lower() == crop_name.lower()), None)
    if profile is None:
        profile = CROP_PROFILES[0]

    deficits = {
        "Nitrogen": max(0.0, profile.nitrogen_min - nitrogen),
        "Phosphorus": max(0.0, profile.phosphorus_min - phosphorus),
        "Potassium": max(0.0, profile.potassium_min - potassium),
    }
    low = [k for k, v in deficits.items() if v > 0]

    if not low:
        status = "Good"
        usage = [
            "Use a maintenance dose of balanced NPK as per local recommendations.",
            "Split application across growth stages instead of applying everything at once.",
            "Re-test soil mid-season if growth slows or leaves discolor.",
        ]
    else:
        status = "Needs improvement"
        usage = [
            f"Focus on {', '.join(low)} first (based on your current soil NPK).",
            "Apply fertilizer in 2-3 splits to reduce nutrient loss.",
            "Water after application and avoid applying before heavy rainfall.",
        ]

    return {
        "crop": profile.name,
        "focus": profile.fertilizer_focus,
        "status": status,
        "nutrients_to_improve": low or ["Routine monitoring only"],
        "usage_instructions": usage,
        "nutrient_deficits": deficits,
        "nutrient_scores": {
            "Nitrogen": _score(nitrogen, profile.nitrogen_min),
            "Phosphorus": _score(phosphorus, profile.phosphorus_min),
            "Potassium": _score(potassium, profile.potassium_min),
        },
    }


def _score(value: float, target_min: float) -> int:
    if target_min <= 0:
        return 100
    ratio = value / target_min
    ratio = 0.0 if ratio < 0 else ratio
    percent = int(min(100.0, ratio * 100.0))
    return percent
