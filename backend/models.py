# backend/models.py
import os
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import scoped_session, sessionmaker

try:
    # Flask está presente en runtime; evitamos fallar si se importa fuera de app context
    from flask import current_app
except Exception:  # pragma: no cover
    current_app = None  # type: ignore

Base = automap_base()

_engine = None  # type: ignore
_Session = None  # type: ignore
_prepared = False

def _resolve_database_url():
    """
    Resuelve la URL de la BD:
    1) Si Flask config tiene "DATABASE_URL": úsala.
    2) Si Flask config tiene "DATABASE": si es ruta SQLite -> sqlite:///<ruta>.
    3) Por defecto: instance/gestion_avisos.sqlite (SQLite).
    """
    # Si hay app context y DATABASE_URL
    if current_app and current_app.config.get("DATABASE_URL"):
        return current_app.config["DATABASE_URL"]

    # Si hay app context y DATABASE como ruta
    if current_app and current_app.config.get("DATABASE"):
        db_path = current_app.config["DATABASE"]
        if db_path.startswith("sqlite:"):
            return db_path
        return f"sqlite:///{db_path}"

    # Fallback: instance/gestion_avisos.sqlite
    instance_path = None
    if current_app:
        instance_path = current_app.instance_path
    else:
        # Caer a ./instance si no hay app context
        instance_path = os.path.join(os.getcwd(), "instance")
    os.makedirs(instance_path, exist_ok=True)
    default_sqlite = os.path.join(instance_path, "gestion_avisos.sqlite")
    return f"sqlite:///{default_sqlite}"

def _ensure_engine():
    global _engine, _Session
    if _engine is None:
        db_url = _resolve_database_url()
        _engine = create_engine(db_url, future=True)
        _Session = scoped_session(sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True))
    return _engine, _Session

def _prepare_mappings():
    global _prepared
    if not _prepared:
        engine, _ = _ensure_engine()
        # Automap lazy: reflejar todo el esquema existente
        Base.prepare(autoload_with=engine)
        _prepared = True
        print(f"Automap reflected tables: {Base.classes.keys()}") # Always print for debug

@contextmanager
def session_scope():
    """
    Context manager para sesiones ORM.
    """
    _, Session = _ensure_engine()
    sess = Session()
    try:
        yield sess
        sess.commit()
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()

@lru_cache(maxsize=128)
def get_table_class(table_name: str):
    """
    Devuelve la clase ORM reflejada para una tabla por su nombre exacto.
    Ej: get_table_class("tickets"), get_table_class("clientes"), get_table_class("providers")
    """
    _prepare_mappings()
    # Base.classes expone cada tabla como atributo. Si no existe, KeyError.
    try:
        return getattr(Base.classes, table_name)
    except AttributeError as e:
        raise LookupError(f"Tabla no encontrada en metadata reflejada: {table_name}") from e

def has_table(table_name: str) -> bool:
    """
    True si la tabla existe tras reflexión.
    """
    _prepare_mappings()
    return hasattr(Base.classes, table_name)
