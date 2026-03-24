from dataclasses import dataclass


@dataclass(frozen=True)
class CropProfile:
    name: str
    season: str
    nitrogen_min: float
    phosphorus_min: float
    potassium_min: float
    temp_min: float
    temp_max: float
    humidity_min: float
    rainfall_min: float
    ph_min: float
    ph_max: float
    fertilizer_focus: str


CROP_PROFILES = [
    CropProfile("Rice", "Kharif", 70, 35, 35, 20, 35, 70, 150, 5.0, 7.0, "Nitrogen-rich fertilizer"),
    CropProfile("Maize", "Kharif", 50, 25, 20, 18, 32, 55, 60, 5.5, 7.5, "Balanced NPK fertilizer"),
    CropProfile("Cotton", "Kharif", 45, 25, 25, 21, 35, 50, 50, 5.8, 8.0, "Potassium-support fertilizer"),
    CropProfile("Groundnut", "Rabi", 20, 30, 25, 20, 30, 50, 40, 6.0, 7.5, "Phosphorus-rich fertilizer"),
    CropProfile("Tomato", "Rabi", 45, 30, 30, 18, 30, 55, 50, 6.0, 7.5, "Balanced NPK with micronutrients"),
    CropProfile("Chilli", "Summer", 40, 25, 30, 20, 33, 50, 40, 6.0, 7.5, "Potassium-rich fertilizer"),
    CropProfile("Sugarcane", "Annual", 80, 35, 35, 20, 38, 60, 100, 6.0, 8.0, "Nitrogen and potassium fertilizer"),
]


def build_advisory(
    *,
    nitrogen: float,
    phosphorus: float,
    potassium: float,
    temperature: float,
    humidity: float,
    rainfall: float,
    ph: float,
    season: str,
    crop_name: str,
) -> dict:
    recommended_crop, crop_scores = recommend_crop(
        nitrogen=nitrogen,
        phosphorus=phosphorus,
        potassium=potassium,
        temperature=temperature,
        humidity=humidity,
        rainfall=rainfall,
        ph=ph,
        season=season,
    )

    fertilizer_target = crop_name or recommended_crop["name"]
    fertilizer_plan = recommend_fertilizer(
        crop_name=fertilizer_target,
        nitrogen=nitrogen,
        phosphorus=phosphorus,
        potassium=potassium,
    )

    return {
        "recommended_crop": recommended_crop,
        "top_matches": crop_scores[:3],
        "fertilizer_plan": fertilizer_plan,
    }


def recommend_crop(
    *,
    nitrogen: float,
    phosphorus: float,
    potassium: float,
    temperature: float,
    humidity: float,
    rainfall: float,
    ph: float,
    season: str,
) -> tuple[dict, list[dict]]:
    scored_profiles = []

    for profile in CROP_PROFILES:
        score = 0
        notes = []

        if season and season.lower() == profile.season.lower():
            score += 20
            notes.append("Season aligned")
        elif profile.season == "Annual":
            score += 10
            notes.append("Works across long growing windows")

        if nitrogen >= profile.nitrogen_min:
            score += 10
        else:
            notes.append("Nitrogen is slightly low")

        if phosphorus >= profile.phosphorus_min:
            score += 10
        else:
            notes.append("Phosphorus may need support")

        if potassium >= profile.potassium_min:
            score += 10
        else:
            notes.append("Potassium may need support")

        if profile.temp_min <= temperature <= profile.temp_max:
            score += 15
            notes.append("Temperature suitable")

        if humidity >= profile.humidity_min:
            score += 10

        if rainfall >= profile.rainfall_min:
            score += 15
            notes.append("Rainfall adequate")

        if profile.ph_min <= ph <= profile.ph_max:
            score += 10
            notes.append("Soil pH suitable")

        scored_profiles.append(
            {
                "name": profile.name,
                "season": profile.season,
                "score": score,
                "summary": "; ".join(notes) or "General fit for the given conditions",
            }
        )

    scored_profiles.sort(key=lambda item: item["score"], reverse=True)
    best = scored_profiles[0]
    best["reason"] = f"{best['name']} matches the strongest combination of season, soil nutrients, weather, and pH."
    return best, scored_profiles


def recommend_fertilizer(
    *,
    crop_name: str,
    nitrogen: float,
    phosphorus: float,
    potassium: float,
) -> dict:
    profile = next(
        (item for item in CROP_PROFILES if item.name.lower() == crop_name.lower()),
        CROP_PROFILES[0],
    )

    nutrients_to_improve = []
    if nitrogen < profile.nitrogen_min:
        nutrients_to_improve.append("Nitrogen")
    if phosphorus < profile.phosphorus_min:
        nutrients_to_improve.append("Phosphorus")
    if potassium < profile.potassium_min:
        nutrients_to_improve.append("Potassium")

    if not nutrients_to_improve:
        message = "Current soil profile is reasonably aligned. Use a maintenance dose and monitor crop growth."
    else:
        message = f"Improve {', '.join(nutrients_to_improve)} levels before or during the crop cycle."

    return {
        "crop": profile.name,
        "focus": profile.fertilizer_focus,
        "message": message,
        "nutrients_to_improve": nutrients_to_improve or ["Routine monitoring only"],
    }
