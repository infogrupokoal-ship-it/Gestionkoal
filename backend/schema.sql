DROP TABLE IF EXISTS error_log;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS permissions;
DROP TABLE IF EXISTS clientes;
DROP TABLE IF EXISTS direcciones;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS servicios;
DROP TABLE IF EXISTS job_services;
DROP TABLE IF EXISTS providers;
DROP TABLE IF EXISTS materiales;
DROP TABLE IF EXISTS job_materials;
DROP TABLE IF EXISTS stock_movements;
DROP TABLE IF EXISTS presupuestos;
DROP TABLE IF EXISTS presupuesto_items;
DROP TABLE IF EXISTS ticket_tareas;
DROP TABLE IF EXISTS gastos_compartidos;
DROP TABLE IF EXISTS whatsapp_message_logs;
DROP TABLE IF EXISTS whatsapp_logs;
DROP TABLE IF EXISTS provider_quotes;
DROP TABLE IF EXISTS market_research;
DROP TABLE IF EXISTS eventos;
DROP TABLE IF EXISTS assets;
DROP TABLE IF EXISTS asset_loans;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS feedback;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS financial_transactions;
DROP TABLE IF EXISTS ficheros;
DROP TABLE IF EXISTS scheduled_maintenance;
DROP TABLE IF EXISTS material_research;
DROP TABLE IF EXISTS whatsapp_templates;
DROP TABLE IF EXISTS user_permissions;
DROP TABLE IF EXISTS role_permissions;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE,
    nombre TEXT,
    apellidos TEXT,
    telefono TEXT,
    direccion TEXT,
    ciudad TEXT,
    provincia TEXT,
    cp TEXT,
    nif TEXT UNIQUE,
    fecha_alta TEXT DEFAULT CURRENT_TIMESTAMP,
    last_login TEXT,
    is_active INTEGER DEFAULT 1,
    is_admin INTEGER DEFAULT 0,
    role TEXT, -- Deprecated, use user_roles table
    whatsapp_number TEXT,
    whatsapp_opt_in INTEGER DEFAULT 0,
    costo_por_hora REAL DEFAULT 0.0, -- New column
    tasa_recargo REAL DEFAULT 0.0, -- New column
    whatsapp_verified INTEGER DEFAULT 0,
    whatsapp_code TEXT,
    whatsapp_code_expires TEXT
);

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE
);

CREATE TABLE error_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    endpoint TEXT,
    method TEXT,
    error_message TEXT NOT NULL,
    traceback TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS clientes (
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

CREATE TABLE IF NOT EXISTS direcciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    linea1 TEXT NOT NULL,
    linea2 TEXT,
    ciudad TEXT,
    provincia TEXT,
    cp TEXT,
    pais TEXT DEFAULT 'EspaÃ±a',
    FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    direccion_id INTEGER,
    equipo_id INTEGER,
    source TEXT, -- e.g., 'phone', 'email', 'web', 'whatsapp'
    tipo TEXT NOT NULL, -- e.g., 'reparacion', 'instalacion', 'mantenimiento'
    prioridad TEXT DEFAULT 'Media', -- 'Baja', 'Media', 'Alta', 'Urgente'
    estado TEXT DEFAULT 'Abierto', -- 'Abierto', 'En Progreso', 'Pendiente', 'Cerrado', 'Cancelado'
    sla_due TEXT, -- Fecha y hora de vencimiento del SLA
    asignado_a INTEGER, -- ID del usuario (tÃ©cnico/autÃ³nomo) asignado
    creado_por INTEGER NOT NULL, -- ID del usuario que creÃ³ el ticket
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
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
    estado_pago TEXT DEFAULT 'Pendiente', -- 'Pendiente', 'Facturado', 'Pagado', 'Reembolsado'
    fecha_pago TEXT,
    provision_fondos REAL,
    fecha_transferencia TEXT,
    recibo_url TEXT,
    payment_confirmation_token TEXT,
    payment_confirmation_expires TEXT,
    job_difficulty_rating INTEGER, -- 1-5 scale
    FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE,
    FOREIGN KEY (direccion_id) REFERENCES direcciones (id) ON DELETE SET NULL,
    FOREIGN KEY (asignado_a) REFERENCES users (id) ON DELETE SET NULL,
    FOREIGN KEY (creado_por) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL,
    category TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS job_services (
    job_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    price_per_unit REAL NOT NULL,
    total_price REAL NOT NULL,
    PRIMARY KEY (job_id, service_id),
    FOREIGN KEY (job_id) REFERENCES tickets (id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES servicios (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS providers (
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
    whatsapp_opt_in INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS materiales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    categoria TEXT,
    unidad TEXT, -- e.g., 'unidad', 'metro', 'kg', 'litro'
    stock REAL DEFAULT 0,
    stock_min REAL DEFAULT 0,
    ubicacion TEXT,
    costo_unitario REAL,
    precio_venta REAL,
    proveedor_principal INTEGER,
    fecha_ultima_compra TEXT,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (proveedor_principal) REFERENCES providers (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS job_materials (
    job_id INTEGER NOT NULL,
    material_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    price_per_unit REAL NOT NULL,
    total_price REAL NOT NULL,
    PRIMARY KEY (job_id, material_id),
    FOREIGN KEY (job_id) REFERENCES tickets (id) ON DELETE CASCADE,
    FOREIGN KEY (material_id) REFERENCES materiales (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL,
    tipo TEXT NOT NULL, -- 'entrada', 'salida', 'ajuste'
    cantidad REAL NOT NULL,
    fecha TEXT DEFAULT CURRENT_TIMESTAMP,
    responsable INTEGER,
    observaciones TEXT,
    FOREIGN KEY (material_id) REFERENCES materiales (id) ON DELETE CASCADE,
    FOREIGN KEY (responsable) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS presupuestos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    freelancer_id INTEGER, -- Added for freelancer quotes
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
    estado TEXT DEFAULT 'Pendiente', -- 'Pendiente', 'Aprobado', 'Rechazado', 'Facturado'
    total REAL NOT NULL,
    billing_entity_type TEXT, -- 'Cliente' or 'Proveedor'
    billing_entity_id INTEGER,
    client_signature_data TEXT,
    client_signature_date TEXT,
    client_signed_by TEXT,
    signed_pdf_url TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets (id) ON DELETE CASCADE,
    FOREIGN KEY (freelancer_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS presupuesto_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    presupuesto_id INTEGER NOT NULL,
    descripcion TEXT NOT NULL,
    qty REAL NOT NULL,
    precio_unit REAL NOT NULL,
    FOREIGN KEY (presupuesto_id) REFERENCES presupuestos (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ticket_tareas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    descripcion TEXT NOT NULL,
    estado TEXT DEFAULT 'Pendiente', -- 'Pendiente', 'En Progreso', 'Completada', 'Cancelada'
    fecha_vencimiento TEXT,
    asignado_a INTEGER,
    creado_por INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    metodo_pago TEXT,
    estado_pago TEXT DEFAULT 'Pendiente',
    provision_fondos REAL,
    fecha_transferencia TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets (id) ON DELETE CASCADE,
    FOREIGN KEY (asignado_a) REFERENCES users (id) ON DELETE SET NULL,
    FOREIGN KEY (creado_por) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS gastos_compartidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    descripcion TEXT NOT NULL,
    monto REAL NOT NULL,
    fecha TEXT DEFAULT CURRENT_TIMESTAMP,
    creado_por INTEGER NOT NULL,
    pagado_por INTEGER, -- Usuario que realizÃ³ el pago (puede ser diferente al creador)
    FOREIGN KEY (ticket_id) REFERENCES tickets (id) ON DELETE CASCADE,
    FOREIGN KEY (creado_por) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (pagado_por) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS whatsapp_message_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    material_id INTEGER,
    provider_id INTEGER,
    direction TEXT NOT NULL, -- 'inbound' or 'outbound'
    from_number TEXT,
    to_number TEXT,
    message_body TEXT NOT NULL,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    whatsapp_message_id TEXT,
    status TEXT, -- e.g., 'sent', 'delivered', 'read', 'failed', 'received', 'processed', 'unprocessed'
    error_info TEXT,
    FOREIGN KEY (job_id) REFERENCES tickets (id) ON DELETE SET NULL,
    FOREIGN KEY (material_id) REFERENCES materiales (id) ON DELETE SET NULL,
    FOREIGN KEY (provider_id) REFERENCES providers (id) ON DELETE SET NULL
);

-- Idempotencia persistente: un mensaje de WhatsApp no debe procesarse dos veces
CREATE UNIQUE INDEX IF NOT EXISTS uq_whatsapp_message_logs_message_id
ON whatsapp_message_logs(whatsapp_message_id);

CREATE TABLE IF NOT EXISTS provider_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    material_id INTEGER NOT NULL,
    provider_id INTEGER NOT NULL,
    quote_amount REAL,
    quote_currency TEXT DEFAULT 'EUR',
    quote_date TEXT,
    response_message TEXT,
    status TEXT DEFAULT 'pending', -- pending, received, rejected, accepted
    whatsapp_message_id TEXT,
    payment_status TEXT DEFAULT 'pending', -- New column
    payment_date TEXT, -- New column
    FOREIGN KEY (job_id) REFERENCES tickets (id) ON DELETE CASCADE,
    FOREIGN KEY (material_id) REFERENCES materiales (id) ON DELETE CASCADE,
    FOREIGN KEY (provider_id) REFERENCES providers (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS market_research (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL,
    sector TEXT,
    price_avg REAL,
    price_min REAL,
    price_max REAL,
    sources_json TEXT,            -- JSON con array de {url,price,date,notes}
    difficulty TEXT,              -- facil|medio|dificil
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (material_id) REFERENCES materiales (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    inicio TEXT NOT NULL, -- Fecha y hora de inicio
    fin TEXT,     -- Fecha y hora de fin
    estado TEXT DEFAULT 'planificado', -- 'planificado', 'completado', 'cancelado'
    tecnico_id INTEGER, -- ID del tÃ©cnico/autÃ³nomo asignado al evento
    FOREIGN KEY (ticket_id) REFERENCES tickets (id) ON DELETE CASCADE,
    FOREIGN KEY (tecnico_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    asset_type TEXT, -- e.g., 'tool', 'vehicle', 'equipment'
    serial_number TEXT UNIQUE,
    purchase_date TEXT,
    warranty_expires TEXT,
    status TEXT DEFAULT 'available', -- 'available', 'in_use', 'under_maintenance', 'retired'
    location TEXT,
    assigned_to INTEGER, -- User ID if assigned to a person
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_to) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS asset_loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL, -- User who borrowed the asset
    loan_date TEXT DEFAULT CURRENT_TIMESTAMP,
    return_date TEXT,
    expected_return_date TEXT,
    status TEXT DEFAULT 'borrowed', -- 'borrowed', 'returned', 'overdue'
    FOREIGN KEY (asset_id) REFERENCES assets (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    rating INTEGER, -- e.g., 1-5 stars
    comments TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id INTEGER,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    details TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS financial_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER,
    type TEXT NOT NULL, -- 'income', 'expense'
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'EUR',
    description TEXT,
    transaction_date TEXT DEFAULT CURRENT_TIMESTAMP,
    recorded_by INTEGER,
    vat_rate REAL,
    vat_amount REAL,
    FOREIGN KEY (ticket_id) REFERENCES tickets (id) ON DELETE SET NULL,
    FOREIGN KEY (recorded_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ficheros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    presupuesto_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    tipo TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (presupuesto_id) REFERENCES presupuestos (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scheduled_maintenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    description TEXT,
    schedule_date TEXT NOT NULL,
    frequency TEXT, -- e.g., 'monthly', 'quarterly', 'annually'
    status TEXT DEFAULT 'scheduled', -- 'scheduled', 'completed', 'cancelled'
    assigned_to INTEGER,
    last_completed TEXT,
    next_due TEXT,
    FOREIGN KEY (asset_id) REFERENCES assets (id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS material_research (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL,
    search_query TEXT NOT NULL,
    search_results_json TEXT, -- JSON array of search results
    analysis_summary TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (material_id) REFERENCES materiales (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS whatsapp_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    template_id TEXT UNIQUE NOT NULL, -- Meta's template ID
    category TEXT, -- e.g., 'utility', 'marketing'
    language TEXT DEFAULT 'es',
    body TEXT NOT NULL,
    example_params TEXT, -- JSON string of example parameters
    status TEXT DEFAULT 'approved', -- 'approved', 'pending', 'rejected'
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_permissions (
    user_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, permission_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE CASCADE
);

-- All INSERT statements moved to the end
INSERT OR IGNORE INTO permissions (code, descripcion) VALUES ('view_reports', 'Ver informes contables');

INSERT OR IGNORE INTO roles (id, code, descripcion) VALUES
(1,'admin','Admin'),
(2,'oficina','Persona de oficina'),
(3,'tecnico','Tecnico'),
(4,'autonomo','Colaborador externo'),
(5,'cliente','Cliente'),
(6,'proveedor','Proveedor');

INSERT OR IGNORE INTO users (id, username, password_hash, role, whatsapp_verified) VALUES
(1, 'admin',    'pbkdf2:sha256:...', 'admin',    1),
(2, 'autonomo', 'pbkdf2:sha256:...', 'autonomo', 1);

INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES
(1, 1),
(2, 4);

