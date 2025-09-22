DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS clientes;
DROP TABLE IF EXISTS direcciones;
DROP TABLE IF EXISTS equipos;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS ticket_mensajes;
DROP TABLE IF EXISTS eventos;
DROP TABLE IF EXISTS checklists;
DROP TABLE IF EXISTS checklist_items;
DROP TABLE IF EXISTS evento_checklist_valores;
DROP TABLE IF EXISTS services;
DROP TABLE IF EXISTS materiales;
DROP TABLE IF EXISTS stock_movs;
DROP TABLE IF EXISTS herramientas;
DROP TABLE IF EXISTS prestamos_herramienta;
DROP TABLE IF EXISTS presupuestos;
DROP TABLE IF EXISTS presupuesto_items;
DROP TABLE IF EXISTS facturas;
DROP TABLE IF EXISTS garantias;
DROP TABLE IF EXISTS ficheros;
DROP TABLE IF EXISTS consentimientos;
DROP TABLE IF EXISTS auditoria;
DROP TABLE IF EXISTS error_log;
DROP TABLE IF EXISTS notifications;

-- Consolidated SQLite Schema for Gestionkoal

-- Roles
CREATE TABLE roles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL, -- admin, oficina, jefe_obra, tecnico, autonomo, cliente
  descripcion TEXT
);

-- Users (renamed from 'usuarios' and merged with 'users' from backend/schema.sql)
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT, -- This will store the role code (e.g., 'admin', 'cliente')
  nombre TEXT,
  telefono TEXT,
  email TEXT,
  nif TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- User Roles (for many-to-many relationship between users and roles)
CREATE TABLE user_roles (
  user_id INTEGER NOT NULL,
  role_id INTEGER NOT NULL,
  PRIMARY KEY (user_id, role_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- Clients
CREATE TABLE clientes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL UNIQUE,
  telefono TEXT,
  email TEXT,
  nif TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Addresses
CREATE TABLE direcciones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cliente_id INTEGER,
  linea1 TEXT,
  linea2 TEXT,
  ciudad TEXT,
  provincia TEXT,
  cp TEXT,
  notas TEXT,
  geo_lat REAL,
  geo_lng REAL,
  FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

-- Equipment
CREATE TABLE equipos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  direccion_id INTEGER,
  marca TEXT,
  modelo TEXT,
  gas TEXT,
  num_serie TEXT,
  instalado_en TEXT, -- DATE in SQLite is TEXT
  notas TEXT,
  FOREIGN KEY (direccion_id) REFERENCES direcciones(id)
);

-- Tickets (Jobs/Tareas)
CREATE TABLE tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cliente_id INTEGER,
  direccion_id INTEGER,
  equipo_id INTEGER,
  source TEXT, -- whatsapp, web, llamada, wallapop
  tipo TEXT, -- mantenimiento, averia, instalacion, vertical, impermeabilizacion
  prioridad TEXT, -- baja, media, alta, urgente
  estado TEXT DEFAULT 'abierto',
  sla_due TEXT, -- TIMESTAMP in SQLite is TEXT
  asignado_a INTEGER,
  creado_por INTEGER,
  descripcion TEXT,
  metodo_pago TEXT,
  estado_pago TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (cliente_id) REFERENCES clientes(id),
  FOREIGN KEY (direccion_id) REFERENCES direcciones(id),
  FOREIGN KEY (equipo_id) REFERENCES equipos(id),
  FOREIGN KEY (asignado_a) REFERENCES users(id),
  FOREIGN KEY (creado_por) REFERENCES users(id)
);

-- Ticket Messages
CREATE TABLE ticket_mensajes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER,
  canal TEXT, -- whatsapp, email, llamada
  direccion TEXT, -- inbound/outbound
  contenido TEXT,
  adjunto_url TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);

-- Events
CREATE TABLE eventos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER,
  tecnico_id INTEGER,
  inicio TEXT, -- TIMESTAMP in SQLite is TEXT
  fin TEXT, -- TIMESTAMP in SQLite is TEXT
  estado TEXT, -- planificado, en_progreso, finalizado
  notas TEXT,
  geo_inicio_lat REAL,
  geo_inicio_lng REAL,
  geo_fin_lat REAL,
  geo_fin_lng REAL,
  firma_url TEXT,
  FOREIGN KEY (ticket_id) REFERENCES tickets(id),
  FOREIGN KEY (tecnico_id) REFERENCES users(id)
);

-- Checklists
CREATE TABLE checklists (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT,
  version TEXT,
  activo BOOLEAN DEFAULT TRUE
);

-- Checklist Items
CREATE TABLE checklist_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  checklist_id INTEGER,
  orden INTEGER,
  etiqueta TEXT,
  requiere_foto BOOLEAN DEFAULT FALSE,
  tipo_valor TEXT, -- numero, texto, booleano
  FOREIGN KEY (checklist_id) REFERENCES checklists(id)
);

-- Event Checklist Values
CREATE TABLE evento_checklist_valores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  evento_id INTEGER,
  checklist_item_id INTEGER,
  valor TEXT,
  foto_url TEXT,
  FOREIGN KEY (evento_id) REFERENCES eventos(id),
  FOREIGN KEY (checklist_item_id) REFERENCES checklist_items(id)
);

-- Services
CREATE TABLE services (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  price REAL,
  recommended_price REAL,
  last_sold_price REAL,
  category TEXT
);

-- Materials
CREATE TABLE materiales (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sku TEXT UNIQUE,
  ean TEXT,
  nombre TEXT,
  categoria TEXT,
  unidad TEXT,
  stock REAL DEFAULT 0, -- NUMERIC in SQLite is REAL
  stock_min REAL DEFAULT 0, -- NUMERIC in SQLite is REAL
  ubicacion TEXT -- taller, furgo1, furgo2...
);

-- Stock Movements
CREATE TABLE stock_movs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  material_id INTEGER,
  qty REAL NOT NULL, -- NUMERIC in SQLite is REAL
  origen TEXT,
  destino TEXT,
  motivo TEXT, -- consumo_ticket, ajuste, compra, traspaso
  ticket_id INTEGER,
  evento_id INTEGER,
  usuario_id INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (material_id) REFERENCES materiales(id),
  FOREIGN KEY (ticket_id) REFERENCES tickets(id),
  FOREIGN KEY (evento_id) REFERENCES eventos(id),
  FOREIGN KEY (usuario_id) REFERENCES users(id)
);

-- Providers
CREATE TABLE proveedores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,
  telefono TEXT,
  email TEXT,
  tipo_proveedor TEXT,
  contacto_persona TEXT,
  direccion TEXT,
  cif TEXT,
  web TEXT,
  notas TEXT,
  condiciones_pago TEXT
);

-- Freelancers
CREATE TABLE freelancers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  category TEXT,
  specialty TEXT,
  city_province TEXT,
  web TEXT,
  notes TEXT,
  source_url TEXT,
  hourly_rate_normal REAL,
  hourly_rate_tier2 REAL,
  hourly_rate_tier3 REAL,
  difficulty_surcharge_rate REAL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Scheduled Maintenances
CREATE TABLE mantenimientos_programados (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cliente_id INTEGER NOT NULL,
  equipo_id INTEGER, -- Optional, if maintenance is for specific equipment
  tipo_mantenimiento TEXT NOT NULL, -- e.g., 'mensual', 'trimestral', 'anual', 'semestral'
  ultima_fecha_mantenimiento TEXT, -- Date of last maintenance
  proxima_fecha_mantenimiento TEXT NOT NULL, -- Date of next scheduled maintenance
  estado TEXT NOT NULL DEFAULT 'activo', -- 'activo', 'pausado', 'completado'
  descripcion TEXT,
  creado_por INTEGER NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (cliente_id) REFERENCES clientes(id),
  FOREIGN KEY (equipo_id) REFERENCES equipos(id),
  FOREIGN KEY (creado_por) REFERENCES users(id)
);

-- Tools
CREATE TABLE herramientas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo TEXT UNIQUE,
  nombre TEXT,
  estado TEXT,
  observaciones TEXT
);

-- Tool Loans
CREATE TABLE prestamos_herramienta (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  herramienta_id INTEGER,
  usuario_id INTEGER,
  salida TEXT, -- TIMESTAMP in SQLite is TEXT
  devolucion TEXT, -- TIMESTAMP in SQLite is TEXT
  estado_salida TEXT,
  estado_entrada TEXT,
  observaciones TEXT,
  FOREIGN KEY (herramienta_id) REFERENCES herramientas(id),
  FOREIGN KEY (usuario_id) REFERENCES users(id)
);

-- Quotes
CREATE TABLE presupuestos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER,
  estado TEXT DEFAULT 'pendiente', -- pendiente, aceptado, rechazado
  total REAL DEFAULT 0, -- NUMERIC in SQLite is REAL
  pdf_url TEXT,
  aceptado_en TEXT, -- TIMESTAMP in SQLite is TEXT
  FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);

-- Quote Items
CREATE TABLE presupuesto_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  presupuesto_id INTEGER,
  sku TEXT,
  descripcion TEXT,
  qty REAL, -- NUMERIC in SQLite is REAL
  precio_unit REAL, -- NUMERIC in SQLite is REAL
  FOREIGN KEY (presupuesto_id) REFERENCES presupuestos(id)
);

-- Invoices
CREATE TABLE facturas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER,
  presupuesto_id INTEGER,
  numero TEXT UNIQUE,
  total REAL, -- NUMERIC in SQLite is REAL
  iva REAL, -- NUMERIC in SQLite is REAL
  cobrado BOOLEAN DEFAULT FALSE,
  link_pago TEXT,
  pdf_url TEXT,
  creada_en TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (ticket_id) REFERENCES tickets(id),
  FOREIGN KEY (presupuesto_id) REFERENCES presupuestos(id)
);

-- Warranties
CREATE TABLE garantias (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER,
  fabricante TEXT,
  poliza TEXT,
  estado TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);

-- Files
CREATE TABLE ficheros (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER,
  evento_id INTEGER,
  url TEXT,
  tipo TEXT, -- foto, pdf, audio, video
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (ticket_id) REFERENCES tickets(id),
  FOREIGN KEY (evento_id) REFERENCES eventos(id)
);

-- Consents
CREATE TABLE consentimientos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cliente_id INTEGER,
  canal TEXT, -- whatsapp, email, marketing
  proposito TEXT,
  texto TEXT,
  dado_en TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

-- Audit Log
CREATE TABLE auditoria (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_id INTEGER,
  accion TEXT,
  entidad TEXT,
  entidad_id INTEGER,
  diff TEXT, -- JSONB in SQLite is TEXT
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (actor_id) REFERENCES users(id)
);

-- Error Log (from backend/schema.sql)
CREATE TABLE error_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  level TEXT NOT NULL,
  message TEXT NOT NULL,
  details TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_tickets_estado ON tickets(estado);
CREATE INDEX IF NOT EXISTS idx_tickets_asignado ON tickets(asignado_a);
CREATE INDEX IF NOT EXISTS idx_materiales_sku ON materiales(sku);
CREATE INDEX IF NOT EXISTS idx_stock_movs_material ON stock_movs(material_id);

-- Notifications
CREATE TABLE notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  is_read BOOLEAN NOT NULL DEFAULT 0,
  message TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);