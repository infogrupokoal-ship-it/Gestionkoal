-- Grupo Koal – Esquema PostgreSQL (MVP)

CREATE TABLE roles (
  id SERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL, -- admin, oficina, jefe_obra, tecnico, autonomo, cliente
  descripcion TEXT
);

CREATE TABLE usuarios (
  id SERIAL PRIMARY KEY,
  nombre TEXT NOT NULL,
  telefono TEXT,
  email TEXT,
  nif TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE clientes (
  id SERIAL PRIMARY KEY,
  nombre TEXT NOT NULL,
  telefono TEXT,
  email TEXT,
  nif TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE direcciones (
  id SERIAL PRIMARY KEY,
  cliente_id INT REFERENCES clientes(id),
  linea1 TEXT,
  linea2 TEXT,
  ciudad TEXT,
  provincia TEXT,
  cp TEXT,
  notas TEXT,
  geo_lat DOUBLE PRECISION,
  geo_lng DOUBLE PRECISION
);

CREATE TABLE equipos (
  id SERIAL PRIMARY KEY,
  direccion_id INT REFERENCES direcciones(id),
  marca TEXT,
  modelo TEXT,
  gas TEXT,
  num_serie TEXT,
  instalado_en DATE,
  notas TEXT
);

CREATE TABLE tickets (
  id SERIAL PRIMARY KEY,
  cliente_id INT REFERENCES clientes(id),
  direccion_id INT REFERENCES direcciones(id),
  equipo_id INT REFERENCES equipos(id),
  source TEXT, -- whatsapp, web, llamada, wallapop
  tipo TEXT, -- mantenimiento, averia, instalacion, vertical, impermeabilizacion
  prioridad TEXT, -- baja, media, alta, urgente
  estado TEXT DEFAULT 'abierto',
  sla_due TIMESTAMP,
  asignado_a INT REFERENCES usuarios(id),
  creado_por INT REFERENCES usuarios(id),
  descripcion TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ticket_mensajes (
  id SERIAL PRIMARY KEY,
  ticket_id INT REFERENCES tickets(id),
  canal TEXT, -- whatsapp, email, llamada
  direccion TEXT, -- inbound/outbound
  contenido TEXT,
  adjunto_url TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE eventos (
  id SERIAL PRIMARY KEY,
  ticket_id INT REFERENCES tickets(id),
  tecnico_id INT REFERENCES usuarios(id),
  inicio TIMESTAMP,
  fin TIMESTAMP,
  estado TEXT, -- planificado, en_progreso, finalizado
  notas TEXT,
  geo_inicio_lat DOUBLE PRECISION,
  geo_inicio_lng DOUBLE PRECISION,
  geo_fin_lat DOUBLE PRECISION,
  geo_fin_lng DOUBLE PRECISION,
  firma_url TEXT
);

CREATE TABLE checklists (
  id SERIAL PRIMARY KEY,
  nombre TEXT,
  version TEXT,
  activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE checklist_items (
  id SERIAL PRIMARY KEY,
  checklist_id INT REFERENCES checklists(id),
  orden INT,
  etiqueta TEXT,
  requiere_foto BOOLEAN DEFAULT FALSE,
  tipo_valor TEXT -- numero, texto, booleano
);

CREATE TABLE evento_checklist_valores (
  id SERIAL PRIMARY KEY,
  evento_id INT REFERENCES eventos(id),
  checklist_item_id INT REFERENCES checklist_items(id),
  valor TEXT,
  foto_url TEXT
);

CREATE TABLE materiales (
  id SERIAL PRIMARY KEY,
  sku TEXT UNIQUE,
  ean TEXT,
  nombre TEXT,
  categoria TEXT,
  unidad TEXT,
  stock NUMERIC DEFAULT 0,
  stock_min NUMERIC DEFAULT 0,
  ubicacion TEXT -- taller, furgo1, furgo2...
);

CREATE TABLE stock_movs (
  id SERIAL PRIMARY KEY,
  material_id INT REFERENCES materiales(id),
  qty NUMERIC NOT NULL,
  origen TEXT,
  destino TEXT,
  motivo TEXT, -- consumo_ticket, ajuste, compra, traspaso
  ticket_id INT REFERENCES tickets(id),
  evento_id INT REFERENCES eventos(id),
  usuario_id INT REFERENCES usuarios(id),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE herramientas (
  id SERIAL PRIMARY KEY,
  codigo TEXT UNIQUE,
  nombre TEXT,
  estado TEXT,
  observaciones TEXT
);

CREATE TABLE prestamos_herramienta (
  id SERIAL PRIMARY KEY,
  herramienta_id INT REFERENCES herramientas(id),
  usuario_id INT REFERENCES usuarios(id),
  salida TIMESTAMP,
  devolucion TIMESTAMP,
  estado_salida TEXT,
  estado_entrada TEXT,
  observaciones TEXT
);

CREATE TABLE presupuestos (
  id SERIAL PRIMARY KEY,
  ticket_id INT REFERENCES tickets(id),
  estado TEXT DEFAULT 'pendiente', -- pendiente, aceptado, rechazado
  total NUMERIC DEFAULT 0,
  pdf_url TEXT,
  aceptado_en TIMESTAMP
);

CREATE TABLE presupuesto_items (
  id SERIAL PRIMARY KEY,
  presupuesto_id INT REFERENCES presupuestos(id),
  sku TEXT,
  descripcion TEXT,
  qty NUMERIC,
  precio_unit NUMERIC
);

CREATE TABLE facturas (
  id SERIAL PRIMARY KEY,
  ticket_id INT REFERENCES tickets(id),
  presupuesto_id INT REFERENCES presupuestos(id),
  numero TEXT UNIQUE,
  total NUMERIC,
  iva NUMERIC,
  cobrado BOOLEAN DEFAULT FALSE,
  link_pago TEXT,
  pdf_url TEXT,
  creada_en TIMESTAMP DEFAULT NOW()
);

CREATE TABLE garantias (
  id SERIAL PRIMARY KEY,
  ticket_id INT REFERENCES tickets(id),
  fabricante TEXT,
  poliza TEXT,
  estado TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ficheros (
  id SERIAL PRIMARY KEY,
  ticket_id INT REFERENCES tickets(id),
  evento_id INT REFERENCES eventos(id),
  url TEXT,
  tipo TEXT, -- foto, pdf, audio, video
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE consentimientos (
  id SERIAL PRIMARY KEY,
  cliente_id INT REFERENCES clientes(id),
  canal TEXT, -- whatsapp, email, marketing
  proposito TEXT,
  texto TEXT,
  dado_en TIMESTAMP DEFAULT NOW()
);

CREATE TABLE auditoria (
  id SERIAL PRIMARY KEY,
  actor_id INT REFERENCES usuarios(id),
  accion TEXT,
  entidad TEXT,
  entidad_id INT,
  diff JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tickets_estado ON tickets(estado);
CREATE INDEX idx_tickets_asignado ON tickets(asignado_a);
CREATE INDEX idx_materiales_sku ON materiales(sku);
CREATE INDEX idx_stock_movs_material ON stock_movs(material_id);

-- Trigger ejemplo: actualizar stock (simple)
CREATE OR REPLACE FUNCTION apply_stock_move() RETURNS TRIGGER AS $$
BEGIN
  UPDATE materiales SET stock = stock + NEW.qty WHERE id = NEW.material_id;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_stock AFTER INSERT ON stock_movs
FOR EACH ROW EXECUTE PROCEDURE apply_stock_move();

-- Usuarios para autenticación
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS error_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  level TEXT NOT NULL,
  message TEXT NOT NULL,
  details TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
