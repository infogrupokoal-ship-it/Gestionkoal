from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import MetaData
from sqlalchemy.ext.automap import automap_base

from backend.extensions import db

# Expose db.Model as Base for Alembic/Flask-Migrate
Base = db.Model


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"sqlite_autoincrement": True}

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    descripcion = db.Column(db.String(255))

    def __repr__(self) -> str:  # pragma: no cover - trivial helper
        return f"<Role {self.code}>"


class UserRole(db.Model):
    __tablename__ = "user_roles"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), primary_key=True)

    role = db.relationship(Role, backref="user_links")


class Client(db.Model):
    __tablename__ = "clientes"
    __table_args__ = {"sqlite_autoincrement": True}

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False, unique=True)
    telefono = db.Column(db.String)
    email = db.Column(db.String)
    nif = db.Column(db.String)
    is_ngo = db.Column(db.Boolean, default=False)
    fecha_alta = db.Column(db.String)

    def __repr__(self) -> str:  # pragma: no cover - trivial helper
        return f"<Client {self.nombre}>"


_AUTOMAP_BASE: type | None = None


def _refresh_automap_cache() -> None:
    global _AUTOMAP_BASE
    _AUTOMAP_BASE = None


def _get_automap_base():
    global _AUTOMAP_BASE
    if _AUTOMAP_BASE is not None:
        return _AUTOMAP_BASE

    engine = db.engine
    metadata = MetaData()
    metadata.reflect(bind=engine)
    Base = automap_base(metadata=metadata)
    Base.prepare()
    _AUTOMAP_BASE = Base
    return Base


def get_table_class(table_name: str):
    """
    Devuelve la clase declarativa para `table_name`. Usa modelos manuales si existen
    y recurre a SQLAlchemy automap cuando no hay modelo explícito.
    """
    for mapper in db.Model.registry.mappers:
        cls = mapper.class_
        if getattr(cls, "__tablename__", None) == table_name:
            return cls

    Base = _get_automap_base()
    try:
        return getattr(Base.classes, table_name)
    except AttributeError:
        _refresh_automap_cache()
        Base = _get_automap_base()
        return getattr(Base.classes, table_name)


@contextmanager
def session_scope(db_instance):
    session = db_instance.session
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
