# backend/models.py
from sqlalchemy import create_engine, text, inspect, Column, Integer, String, Text, ForeignKey, MetaData, Boolean
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from flask import current_app
from contextlib import contextmanager
import os
from .__init__ import db # Import the db instance

Base = automap_base(metadata=db.metadata)

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




def get_table_class(table_name: str):
    """
    Devuelve la clase mapeada para `table_name`.
    1) Busca en mapeos declarativos (db.Model)
    2) Busca en automap (Base.classes)
    No usa db.engine en el bloque de error para no requerir app context.
    """
    # A) Declarativos registrados en db.Model (si existieran)
    for mapper in db.Model.registry.mappers:
        cls = mapper.class_
        if getattr(cls, "__tablename__", None) == table_name:
            return cls

    # B) Automap
    try:
        return Base.classes[table_name]
    except KeyError:
        # SOLO diagnosticamos con lo que ya tenemos cargado en metadata,
        # sin tocar db.engine (evita RuntimeError en tests)
        tablenames = sorted(Base.metadata.tables.keys())
        raise LookupError(
            f"Tabla no encontrada en metadata reflejada: {table_name}. "
            f"Tablas conocidas en metadata: {tablenames}"
        )

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
