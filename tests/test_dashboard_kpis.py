# tests/test_dashboard_kpis.py
import os
import shutil
import sqlite3
import tempfile
import unittest

from backend import create_app


class DashboardKPIsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gk_test_")
        self.db_path = os.path.join(self.tmpdir, "test.sqlite")

        # Crear app y apuntar a la DB temporal
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            DATABASE=self.db_path,
        )
        self.client = self.app.test_client()

        # Preparar tabla mínima de trabajos
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS trabajos (id INTEGER PRIMARY KEY, estado TEXT)")
        # Insertar datos: 3 pendientes, 2 en curso, 1 completado, 1 cancelado = total 7
        rows = [
            ("pendiente",), ("pendiente",), ("pendiente_asignacion",),
            ("en_curso",), ("asignado",),
            ("completado",),
            ("cancelado",),
        ]
        cur.executemany("INSERT INTO trabajos (estado) VALUES (?)", rows)
        conn.commit()
        conn.close()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_kpis_endpoint(self):
        resp = self.client.get("/api/dashboard/kpis")
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertTrue(payload["ok"])
        data = payload["data"]
        # Asserts
        self.assertEqual(data["total"], 7)
        self.assertEqual(data["pendientes"], 3)  # pendiente + pendiente + pendiente_asignacion
        self.assertEqual(data["en_curso"], 2)    # en_curso + asignado
        self.assertEqual(data["completados"], 1)
        self.assertEqual(data["cancelados"], 1)
        self.assertEqual(data["abiertos"], 7 - 1 - 1)  # total - completados - cancelados

if __name__ == "__main__":
    unittest.main()
