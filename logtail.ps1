param(
  [int]$Limit = 20
)

$ErrorActionPreference = "Stop"

# Usar Python del venv si existe
$py = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (!(Test-Path $py)) { $py = "python" }

# Script Python que lee los últimos registros
$code = @"
import sqlite3, os, sys
limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
db = os.path.join('instance','backend.sqlite')
con = sqlite3.connect(db)
rows = con.execute(
    'SELECT id, level, message, COALESCE(details,"") as details, created_at FROM error_log ORDER BY id DESC LIMIT ?',
    (limit,)
).fetchall()

# Salida compacta estilo tabla
print(f'Últimos {limit} registros de error_log en {db}:\\n')
print(f'{"ID":>4}  {"NIVEL":<7}  {"FECHA":<20}  MENSAJE')
print('-'*80)
for r in rows:
    id_, level, message, details, created = r
    if message is None: message = ""
    msg1 = message.replace("\n"," ").strip()
    print(f'{id_:>4}  {level:<7}  {created:<20}  {msg1}')
"@

# Ejecutar
& $py - << 'PY' $Limit
$code
PY