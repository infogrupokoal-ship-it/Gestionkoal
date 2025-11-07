
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
