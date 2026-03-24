from __future__ import annotations


def validate_crop_inputs(
    *,
    nitrogen: float,
    phosphorus: float,
    potassium: float,
    temperature: float,
    humidity: float,
    rainfall: float,
    ph: float,
) -> list[str]:
    errors: list[str] = []
    if nitrogen < 0 or nitrogen > 200:
        errors.append("Nitrogen (N) should be between 0 and 200.")
    if phosphorus < 0 or phosphorus > 200:
        errors.append("Phosphorus (P) should be between 0 and 200.")
    if potassium < 0 or potassium > 200:
        errors.append("Potassium (K) should be between 0 and 200.")
    if temperature < -5 or temperature > 60:
        errors.append("Temperature should be between -5 and 60 °C.")
    if humidity < 0 or humidity > 100:
        errors.append("Humidity should be between 0 and 100%.")
    if rainfall < 0 or rainfall > 1000:
        errors.append("Rainfall should be between 0 and 1000 mm.")
    if ph < 0 or ph > 14:
        errors.append("Soil pH should be between 0 and 14.")
    return errors


def validate_fertilizer_inputs(*, nitrogen: float, phosphorus: float, potassium: float) -> list[str]:
    errors: list[str] = []
    if nitrogen < 0 or nitrogen > 200:
        errors.append("Nitrogen (N) should be between 0 and 200.")
    if phosphorus < 0 or phosphorus > 200:
        errors.append("Phosphorus (P) should be between 0 and 200.")
    if potassium < 0 or potassium > 200:
        errors.append("Potassium (K) should be between 0 and 200.")
    return errors
