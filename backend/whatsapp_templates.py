TEMPLATES = {
    "ack_high": "Aviso recibido (PRIORIDAD ALTA). Nuestro equipo se pone en marcha inmediatamente.",
    "ack_medium": "Gracias por tu aviso. Te contactamos en breve.",
    "ack_low": "Aviso recibido. Te contactamos en el día con propuesta y plazo.",
    "request_more_info": "Para poder ayudarte mejor, ¿podrías enviarnos fotos y la dirección exacta?",
    "scheduled": "Hemos programado la visita para {fecha} con {tecnico}. Gracias.",
    "on_the_way": "Nuestro técnico va en camino. Hora estimada de llegada: {hora}.",
    "resolved": "Tu incidencia se ha resuelto. Si notas algo más, avísanos.",
    "nps_request": "¿Cómo valorarías el servicio del 1 al 10? Tu opinión nos ayuda a mejorar.",
}


def render_template(key: str, **kwargs) -> str:
    base = TEMPLATES.get(key, "")
    try:
        return base.format(**kwargs)
    except Exception:
        return base

