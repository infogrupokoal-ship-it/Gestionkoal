PRAGMA foreign_keys = ON;



-- 1) DROPS (solo aquí, y antes de todo lo demás)
DROP TABLE IF EXISTS user_permissions;
DROP TABLE IF EXISTS role_permissions;
DROP TABLE IF EXISTS whatsapp_templates;
DROP TABLE IF EXISTS material_research;
DROP TABLE IF EXISTS scheduled_maintenance;
DROP TABLE IF EXISTS ficheros;
DROP TABLE IF EXISTS financial_transactions;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS feedback;
DROP TABLE IF EXISTS notifications;   -- ← si la vas a crear luego, dropea aquí y solo aquí
DROP TABLE IF EXISTS asset_loans;
DROP TABLE IF EXISTS assets;
DROP TABLE IF EXISTS eventos;
DROP TABLE IF EXISTS market_research;
DROP TABLE IF EXISTS provider_quotes;
DROP TABLE IF EXISTS whatsapp_logs;
DROP TABLE IF EXISTS ai_logs;
DROP TABLE IF EXISTS sla_events;
DROP TABLE IF EXISTS gastos_compartidos;
DROP TABLE IF EXISTS ticket_tareas;
DROP TABLE IF EXISTS presupuesto_items;
DROP TABLE IF EXISTS presupuestos;
DROP TABLE IF EXISTS stock_movements;
DROP TABLE IF EXISTS job_materials;
DROP TABLE IF EXISTS materiales;
DROP TABLE IF EXISTS providers;
DROP TABLE IF EXISTS job_services;
DROP TABLE IF EXISTS servicios;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS direcciones;
DROP TABLE IF EXISTS clientes;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS permissions;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS error_log;


CREATE TABLE error_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  time TEXT DEFAULT CURRENT_TIMESTAMP,
  message TEXT
);

CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL,
  whatsapp_verified INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    descripcion TEXT
);

CREATE TABLE user_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE,
    UNIQUE (user_id, role_id)
);

CREATE TABLE permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    descripcion TEXT
);

CREATE TABLE clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    email TEXT,
    nif TEXT UNIQUE,
    direccion TEXT,
    ciudad TEXT,
    provincia TEXT,
    cp TEXT,
    fecha_alta TEXT DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    is_ngo INTEGER DEFAULT 0,
    whatsapp_number TEXT,
    whatsapp_opt_in INTEGER DEFAULT 0
);

CREATE TABLE direcciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    linea1 TEXT NOT NULL,
    linea2 TEXT,
    ciudad TEXT,
    provincia TEXT,
    cp TEXT,
    pais TEXT DEFAULT 'España',
    FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
);

CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    direccion_id INTEGER,
    equipo_id INTEGER,
    source TEXT, 
    tipo TEXT NOT NULL, 
    prioridad TEXT DEFAULT 'Media',
    estado TEXT DEFAULT 'Abierto',
    sla_due TEXT,
    asignado_a INTEGER,
    creado_por INTEGER NOT NULL,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Consistent naming
    fecha_inicio TEXT,
    fecha_fin TEXT,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    observaciones TEXT,
    presupuesto_aprobado INTEGER DEFAULT 0,
    costo_estimado REAL,
    costo_real REAL,
    margen_beneficio REAL,
    fecha_cierre TEXT,
    metodo_pago TEXT,
    estado_pago TEXT DEFAULT 'Pendiente',
    fecha_pago TEXT,
    provision_fondos REAL,
    fecha_transferencia TEXT,
    recibo_url TEXT,
    payment_confirmation_token TEXT,
    payment_confirmation_expires TEXT,
    job_difficulty_rating INTEGER,
    FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE,
    FOREIGN KEY (direccion_id) REFERENCES direcciones (id) ON DELETE SET NULL,
    FOREIGN KEY (asignado_a) REFERENCES users (id) ON DELETE SET NULL,
    FOREIGN KEY (creado_por) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL,
    category TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    contacto TEXT,
    telefono TEXT,
    email TEXT,
    direccion TEXT,
    nif TEXT UNIQUE,
    fecha_alta TEXT DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    whatsapp_number TEXT,
    whatsapp_opt_in INTEGER DEFAULT 0,
    tipo_proveedor TEXT
);

CREATE TABLE materiales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    categoria TEXT,
    unidad TEXT,
    stock REAL DEFAULT 0,
    stock_min REAL DEFAULT 0,
    ubicacion TEXT,
    costo_unitario REAL,
    precio_venta REAL,
    proveedor_principal_id INTEGER,
    fecha_ultima_compra TEXT,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (proveedor_principal_id) REFERENCES providers (id) ON DELETE SET NULL
);

CREATE TABLE whatsapp_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  direction TEXT NOT NULL,
  phone TEXT,
  message TEXT,
  provider TEXT,
  status TEXT,
  error TEXT,
  payload JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT,
  input TEXT,
  output TEXT,
  score REAL,
  ticket_id INTEGER,
  client_id INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sla_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER NOT NULL,
  event TEXT,
  details TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  message TEXT NOT NULL,
  is_read INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3) SEED (IDs fijos, para evitar FKs frágiles)
INSERT OR IGNORE INTO roles (id, code, descripcion) VALUES
(1,'admin','Admin'),
(2,'oficina','Persona de oficina'),
(3,'tecnico','Técnico'),
(4,'autonomo','Colaborador externo'),
(5,'cliente','Cliente'),
(6,'proveedor','Proveedor');

INSERT OR IGNORE INTO users (id, username, password_hash, role, whatsapp_verified) VALUES
(1, 'admin',    'pbkdf2:sha256:...','admin',    1),
(2, 'autonomo', 'pbkdf2:sha256:...','autonomo', 1);

INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES
(1, 1),  -- admin → admin
(2, 4);  -- autonomo → autonomo

-- Indexes recomendados
CREATE INDEX IF NOT EXISTS idx_tickets_client_created ON tickets(cliente_id, created_at);