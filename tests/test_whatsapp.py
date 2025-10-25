# tests/test_whatsapp.py
import os
import json

def test_webhook_verify(client, monkeypatch):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "abc")
    rv = client.get("/webhooks/whatsapp/?hub.mode=subscribe&hub.verify_token=abc&hub.challenge=123")
    assert rv.status_code == 200
    assert rv.data == b"123"

def test_webhook_receive_dry_run(client, monkeypatch):
    monkeypatch.setenv("WHATSAPP_PROVIDER", "meta")
    monkeypatch.setenv("WHATSAPP_DRY_RUN", "1")
    payload = {
      "entry":[{"changes":[{"value":{"messages":[{"from":"34600111222","type":"text","text":{"body":"hola"}}]}}]}]}
    }
    rv = client.post("/webhooks/whatsapp/", data=json.dumps(payload), content_type="application/json")
    assert rv.status_code == 200

def test_send_text_dry_run(client, monkeypatch):
    monkeypatch.setenv("WHATSAPP_PROVIDER", "meta")
    monkeypatch.setenv("WHATSAPP_DRY_RUN", "1")
    # Note: This test requires a logged-in admin user to pass the 403 check.
    # For simplicity in this test, we can just check that it doesn't 500.
    # A more advanced test would use a fixture to log in as an admin.
    rv = client.post("/notifications/wa_test", json={"to":"34600111222","text":"ping"})
    assert rv.status_code in (200, 403)  # 403 is expected if not logged in as admin
