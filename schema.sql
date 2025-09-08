-- schema.sql

-- Drop tables in an order that respects foreign key constraints
DROP TABLE IF EXISTS shared_expenses;
DROP TABLE IF EXISTS job_material_install_costs;
DROP TABLE IF EXISTS job_quotes;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS tareas;
DROP TABLE IF EXISTS gastos;
DROP TABLE IF EXISTS stock_movements;
DROP TABLE IF EXISTS materials;
DROP TABLE IF EXISTS services;
DROP TABLE IF EXISTS trabajos;
DROP TABLE IF EXISTS proveedores;
DROP TABLE IF EXISTS freelancer_details;
DROP TABLE IF EXISTS role_permissions;
DROP TABLE IF EXISTS permissions;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS clients;
DROP TABLE IF EXISTS activity_log;


CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    direccion TEXT,
    telefono TEXT,
    whatsapp TEXT,
    email TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS freelancer_details (
    id INTEGER PRIMARY KEY, -- Foreign Key to users.id
    category TEXT,
    specialty TEXT,
    city_province TEXT,
    address TEXT,
    web TEXT,
    phone TEXT,
    whatsapp TEXT,
    notes TEXT,
    source_url TEXT,
    hourly_rate_normal REAL DEFAULT 0.0,
    hourly_rate_tier2 REAL DEFAULT 0.0,
    hourly_rate_tier3 REAL DEFAULT 0.0,
    difficulty_surcharge_rate REAL DEFAULT 0.0,
    FOREIGN KEY (id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    contacto TEXT,
    telefono TEXT,
    email TEXT,
    direccion TEXT,
    tipo TEXT
);

CREATE TABLE IF NOT EXISTS trabajos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    autonomo_id INTEGER,
    proposed_autonomo_id INTEGER,
    approval_status TEXT DEFAULT 'Pending',
    encargado_id INTEGER,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    estado TEXT,
    presupuesto REAL,
    vat_rate REAL DEFAULT 21.0,
    fecha_visita TEXT,
    costo_total_materiales REAL DEFAULT 0,
    costo_total_mano_obra REAL DEFAULT 0,
    completion_date TEXT,
    actual_cost_materials REAL DEFAULT 0,
    actual_cost_labor REAL DEFAULT 0,
    client_feedback TEXT,
    freelancer_rating INTEGER,
    job_difficulty_rating INTEGER DEFAULT 0,
    FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE,
    FOREIGN KEY (autonomo_id) REFERENCES users (id) ON DELETE SET NULL,
    FOREIGN KEY (proposed_autonomo_id) REFERENCES users (id) ON DELETE SET NULL,
    FOREIGN KEY (encargado_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL,
    category TEXT,
    recommended_price REAL DEFAULT 0.0,
    last_sold_price REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    current_stock REAL DEFAULT 0,
    unit_price REAL,
    min_stock_level REAL DEFAULT 0,
    unit_of_measure TEXT,
    recommended_price REAL DEFAULT 0.0,
    last_sold_price REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    quantity REAL NOT NULL,
    movement_date TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY (material_id) REFERENCES materials (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trabajo_id INTEGER NOT NULL,
    descripcion TEXT NOT NULL,
    tipo TEXT NOT NULL,
    monto REAL NOT NULL,
    vat_rate REAL DEFAULT 21.0,
    fecha TEXT NOT NULL,
    FOREIGN KEY (trabajo_id) REFERENCES trabajos (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tareas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trabajo_id INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    estado TEXT DEFAULT 'Pendiente',
    fecha_limite TEXT,
    autonomo_id INTEGER,
    metodo_pago TEXT,
    estado_pago TEXT,
    monto_abonado REAL DEFAULT 0.0,
    fecha_pago TEXT,
    FOREIGN KEY (trabajo_id) REFERENCES trabajos (id) ON DELETE CASCADE,
    FOREIGN KEY (autonomo_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    type TEXT,
    related_id INTEGER,
    is_read BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP NOT NULL,
    snooze_until TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS job_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trabajo_id INTEGER NOT NULL,
    autonomo_id INTEGER NOT NULL,
    quote_date TEXT NOT NULL,
    status TEXT DEFAULT 'Draft',
    total_materials_cost REAL DEFAULT 0.0,
    total_labor_cost REAL DEFAULT 0.0,
    total_services_cost REAL DEFAULT 0.0,
    total_quote_amount REAL DEFAULT 0.0,
    vat_rate REAL DEFAULT 21.0,
    client_notes TEXT,
    freelancer_notes TEXT,
    client_signature_data TEXT,
    client_signature_date TEXT,
    FOREIGN KEY (trabajo_id) REFERENCES trabajos (id) ON DELETE CASCADE,
    FOREIGN KEY (autonomo_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS job_material_install_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    material_id INTEGER,
    service_id INTEGER,
    description TEXT,
    cost REAL NOT NULL,
    revenue REAL,
    date TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY (job_id) REFERENCES trabajos (id) ON DELETE CASCADE,
    FOREIGN KEY (material_id) REFERENCES materials (id) ON DELETE SET NULL,
    FOREIGN KEY (service_id) REFERENCES services (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS shared_expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gasto_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    amount_shared REAL NOT NULL,
    is_billed_to_client BOOLEAN DEFAULT FALSE,
    notes TEXT,
    FOREIGN KEY (gasto_id) REFERENCES gastos (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);