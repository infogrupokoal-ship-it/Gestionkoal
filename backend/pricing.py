# backend/pricing.py
from flask import current_app
from sqlalchemy import text

from backend.extensions import db


def get_market_rate(profession_code: str) -> dict:
    """
    Retrieves the market rate for a given profession code.
    Returns a dictionary with 'min', 'sugerido', 'max' prices.
    """
    rate = db.session.execute(
        text("SELECT precio_min, precio_sugerido_hora, precio_max FROM profession_rates WHERE code = :code"),
        {"code": profession_code}
    ).fetchone()
    if rate:
        return {"min": rate.precio_min, "sugerido": rate.precio_sugerido_hora, "max": rate.precio_max}
    return {"min": 0.0, "sugerido": 0.0, "max": 0.0}

def get_effective_rate(user_id: int, profession_code: str) -> float:
    """
    Retrieves the effective hourly rate for a user and profession.
    Checks for user-specific overrides first, then falls back to the market suggested rate.
    """
    override = db.session.execute(
        text("SELECT precio_hora FROM user_rate_overrides WHERE user_id = :user_id AND profession_code = :profession_code"),
        {"user_id": user_id, "profession_code": profession_code}
    ).fetchone()
    if override:
        return override.precio_hora

    market_rate = get_market_rate(profession_code)
    return market_rate["sugerido"]

def set_override(user_id: int, profession_code: str, precio_hora: float, comentario: str = None, motivo_dificultad: int = 0):
    """
    Sets a user-specific override for a profession's hourly rate and logs the change.
    """
    # Get current suggested market rate for delta calculation
    market_rate = get_market_rate(profession_code)
    sugerido = market_rate["sugerido"]
    delta_porcentaje = ((precio_hora - sugerido) / sugerido * 100) if sugerido != 0 else 0

    # Insert/Update user_rate_overrides
    existing_override = db.session.execute(
        text("SELECT id FROM user_rate_overrides WHERE user_id = :user_id AND profession_code = :profession_code"),
        {"user_id": user_id, "profession_code": profession_code}
    ).fetchone()

    if existing_override:
        db.session.execute(
            text("UPDATE user_rate_overrides SET precio_hora = :precio_hora, comentario = :comentario, motivo_dificultad = :motivo_dificultad, created_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"precio_hora": precio_hora, "comentario": comentario, "motivo_dificultad": motivo_dificultad, "id": existing_override.id}
        )
    else:
        db.session.execute(
            text("INSERT INTO user_rate_overrides (user_id, profession_code, precio_hora, comentario, motivo_dificultad) VALUES (:user_id, :profession_code, :precio_hora, :comentario, :motivo_dificultad)"),
            {"user_id": user_id, "profession_code": profession_code, "precio_hora": precio_hora, "comentario": comentario, "motivo_dificultad": motivo_dificultad}
        )

    # Log the change
    db.session.execute(
        text("INSERT INTO rate_change_log (user_id, profession_code, precio_hora, delta_porcentaje, motivo_dificultad) VALUES (:user_id, :profession_code, :precio_hora, :delta_porcentaje, :motivo_dificultad)"),
        {"user_id": user_id, "profession_code": profession_code, "precio_hora": precio_hora, "delta_porcentaje": delta_porcentaje, "motivo_dificultad": motivo_dificultad}
    )
    db.session.commit()

    # Trigger learning mechanism
    maybe_adjust_market_suggested(profession_code)

def maybe_adjust_market_suggested(profession_code: str):
    """
    Adjusts the market suggested rate based on recent user overrides (learning mechanism).
    """
    # Get last N changes not marked as 'motivo_dificultad'
    N = 20 # Number of recent changes to consider
    changes = db.session.execute(
        text("SELECT user_id, precio_hora, delta_porcentaje FROM rate_change_log WHERE profession_code = :profession_code AND motivo_dificultad = 0 ORDER BY created_at DESC LIMIT :n"),
        {"profession_code": profession_code, "n": N}
    ).fetchall()

    if not changes:
        return

    # Group changes by user to check for consistency
    user_changes = {}
    for change in changes:
        user_id = change.user_id
        if user_id not in user_changes:
            user_changes[user_id] = []
        user_changes[user_id].append(change.precio_hora)

    # Check if any user has >=5 consistent changes
    consistent_changes = []
    for _user_id, rates in user_changes.items():
        if len(rates) >= 5:
            # Check for consistency (e.g., all rates are significantly higher or lower than suggested)
            # For simplicity, we'll just take all rates from users with >=5 changes
            consistent_changes.extend(rates)

    if not consistent_changes:
        return

    # Calculate trimmed mean (e.g., trim 20% from both ends)
    consistent_changes.sort()
    trim_count = int(len(consistent_changes) * 0.2)
    trimmed_rates = consistent_changes[trim_count:-trim_count] if trim_count > 0 else consistent_changes

    if not trimmed_rates:
        return

    new_sugerido = sum(trimmed_rates) / len(trimmed_rates)

    # Clamp new_sugerido between min and max market rates
    market_rate = get_market_rate(profession_code)
    new_sugerido = max(market_rate["min"], min(new_sugerido, market_rate["max"]))

    # Update profession_rates if suggested price has changed significantly
    current_sugerido = market_rate["sugerido"]
    if abs(new_sugerido - current_sugerido) > 0.5: # Only update if change is significant (e.g., > 0.5€)
        db.session.execute(
            text("UPDATE profession_rates SET precio_sugerido_hora = :new_sugerido, updated_at = CURRENT_TIMESTAMP WHERE code = :code"),
            {"new_sugerido": new_sugerido, "code": profession_code}
        )
        db.session.commit()
        current_app.logger.info(f"Market suggested rate for {profession_code} adjusted from {current_sugerido:.2f} to {new_sugerido:.2f}")
