# backend/models.py
from sqlalchemy import create_engine, text, inspect, Column, Integer, String, Text, ForeignKey, MetaData, Boolean
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from flask import current_app
from contextlib import contextmanager
import os
from backend.extensions import db # Import the db instance



class Client(db.Model):
    __tablename__ = 'clientes'
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False, unique=True)
    telefono = Column(String)
    email = Column(String)
    nif = Column(String)
    is_ngo = Column(Boolean, default=False)
    fecha_alta = Column(String)

    def __repr__(self):
        return f'<Client {self.nombre}>'




from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.ext.automap import automap_base
from .__init__ import db # Import the db instance

# Cache simple en módulo para reflejo/automap
__automap_cache = {"metadata": None, "Base": None}

def _ensure_automap():
    """
    Refleja el esquema actual y construye la Base de automap (con cache).
    Requiere app_context activo para acceder a db.engine.
    """
    if __automap_cache["Base"] is None:
        engine = db.engine  # requiere app_context activo
        # Usar la metadata global de Flask‑SQLAlchemy para compatibilidad con tests
        md = db.metadata
        if not md.tables:
            md.reflect(bind=engine)
        Base = automap_base(metadata=md)
        __automap_cache["metadata"] = md
        __automap_cache["Base"] = Base
    return __automap_cache["Base"]

def get_table_class(table_name: str):
    """
    1) Devuelve clases declarativas si existen.
    2) Si no, usa automap dinámico (con cache).
    """
    # Declarativos registrados (si los hubiera)
    for mapper in db.Model.registry.mappers:
        cls = mapper.class_
        if getattr(cls, "__tablename__", None) == table_name:
            return cls

    # Automap
    Base = _ensure_automap()
    try:
        return getattr(Base.classes, table_name)
    except AttributeError:
        # Si la tabla no estaba cuando se generó la cache, reintenta refrescando
        __automap_cache["Base"] = None
        Base = _ensure_automap()
        return getattr(Base.classes, table_name)

@contextmanager
def session_scope(db_instance):
    session = db_instance.session
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

# --- Overrides to stabilize tests (in-memory SQLite) ---
from sqlalchemy.ext.automap import automap_base as _auto
from sqlalchemy import MetaData as _Meta

def _ensure_automap_fallback():
    try:
        eng = db.engine
        md = db.metadata
        if not md or not md.tables:
            md = _Meta()
            md.reflect(bind=eng)
        return _auto(metadata=md)
    except Exception:
        # as last resort, attempt fresh reflect
        md = _Meta()
        md.reflect(bind=db.engine)
        return _auto(metadata=md)

# Redefine get_table_class with recovery

def get_table_class(table_name: str):
    # Declarativos registrados (si los hubiera)
    for mapper in db.Model.registry.mappers:
        cls = mapper.class_
        if getattr(cls, "__tablename__", None) == table_name:
            return cls
    Base = _ensure_automap_fallback()
    try:
        return getattr(Base.classes, table_name)
    except AttributeError:
        # If running on SQLite in-memory, try to load schema.sql and retry
        try:
            from flask import current_app
            uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '') if current_app else ''
            if 'sqlite' in uri and ':memory:' in uri:
                import os
                schema_path = os.path.join(current_app.root_path, '..', 'schema.sql') if current_app else 'schema.sql'
                if os.path.exists(schema_path):
                    with db.engine.begin() as conn:
                        raw = conn.connection
                        with open(schema_path, 'r', encoding='utf-8') as f:
                            raw.executescript(f.read())
        except Exception:
            pass
        Base = _ensure_automap_fallback()
        return getattr(Base.classes, table_name)
