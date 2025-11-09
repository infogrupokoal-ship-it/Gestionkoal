
-- backend/schema.sql

-- ... (contenido existente del schema.sql) ...

-- Tabla para logs de sugerencias de IA
CREATE TABLE IF NOT EXISTS ai_suggestion_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    prompt_sent TEXT,
    response_received TEXT,
    suggestion_accepted BOOLEAN,
    confidence_score REAL,
    model_used TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Tabla para facturas
CREATE TABLE IF NOT EXISTS facturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER,
    quote_id INTEGER,
    client_id INTEGER NOT NULL,
    fecha_emision DATE NOT NULL,
    fecha_vencimiento DATE,
    total_bruto REAL NOT NULL,
    total_iva REAL NOT NULL,
    total_neto REAL NOT NULL,
    estado TEXT NOT NULL DEFAULT 'borrador', -- borrador, emitida, pagada, anulada
    pdf_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES tickets (id),
    FOREIGN KEY (quote_id) REFERENCES presupuestos (id),
    FOREIGN KEY (client_id) REFERENCES clientes (id)
);

-- Tabla para partes de horas
CREATE TABLE IF NOT EXISTS partes_horas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL, -- Autónomo o empleado que registra las horas
    fecha DATE NOT NULL,
    horas_trabajadas REAL NOT NULL,
    descripcion TEXT,
    tarifa_hora REAL,
    costo_total REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Tabla para liquidaciones a autónomos
CREATE TABLE IF NOT EXISTS liquidaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    autonomo_id INTEGER NOT NULL,
    fecha_liquidacion DATE NOT NULL,
    periodo_inicio DATE NOT NULL,
    periodo_fin DATE NOT NULL,
    monto_total REAL NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente', -- pendiente, pagada, anulada
    pdf_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (autonomo_id) REFERENCES users (id)
);
