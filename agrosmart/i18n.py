from __future__ import annotations

from flask import request, session


SUPPORTED_LANGS: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
}


TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "nav_dashboard": "Dashboard",
        "nav_profile": "Profile",
        "nav_admin": "Admin",
        "nav_login": "Login",
        "lang_label": "Language",
        "voice_speak": "Speak",
        "voice_stop": "Stop",
        "crop_title": "Predict best crop",
        "fert_title": "Improve soil nutrition",
        "disease_title": "Upload leaf image",
    },
    "hi": {
        "nav_dashboard": "डैशबोर्ड",
        "nav_profile": "प्रोफ़ाइल",
        "nav_admin": "एडमिन",
        "nav_login": "लॉगिन",
        "lang_label": "भाषा",
        "voice_speak": "सुनाएँ",
        "voice_stop": "रोकें",
        "crop_title": "सर्वश्रेष्ठ फसल बताएं",
        "fert_title": "मिट्टी पोषण सुधारें",
        "disease_title": "पत्ती की छवि अपलोड करें",
    },
    "te": {
        "nav_dashboard": "డ్యాష్‌బోర్డ్",
        "nav_profile": "ప్రొఫైల్",
        "nav_admin": "అడ్మిన్",
        "nav_login": "లాగిన్",
        "lang_label": "భాష",
        "voice_speak": "చదవండి",
        "voice_stop": "ఆపండి",
        "crop_title": "ఉత్తమ పంట సూచన",
        "fert_title": "మట్టీ పోషణ మెరుగుదల",
        "disease_title": "ఆకు చిత్రం అప్లోడ్",
    },
}


def get_lang() -> str:
    lang = (request.args.get("lang") or session.get("lang") or "en").strip().lower()
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    session["lang"] = lang
    return lang


def t(key: str) -> str:
    lang = get_lang()
    return TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS["en"].get(key, key))

