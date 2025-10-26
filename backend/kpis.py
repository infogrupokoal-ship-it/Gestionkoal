# backend/kpis.py
from datetime import datetime, timedelta

def estimate_sla_due(priority: str) -> str:
    now = datetime.utcnow()
    if priority == 'alta':
        sla_time = now + timedelta(hours=4)
    elif priority == 'baja':
        sla_time = now + timedelta(hours=72)
    else: # media
        sla_time = now + timedelta(hours=24)
    return sla_time.strftime('%Y-%m-%d %H:%M:%S')
