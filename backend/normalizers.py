# backend/normalizers.py

def normalize_phone(phone: str) -> str:
    # Simple normalizer, can be expanded (e.g., with phonenumbers library)
    if not phone:
        return ""
    return "".join(filter(str.isdigit, phone))

def normalize_priority(prio: str) -> str:
    p = (prio or "").lower().strip()
    if p in ["alta", "urgente"]:
        return "alta"
    if p in ["baja"]:
        return "baja"
    return "media"
