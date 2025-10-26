import json
from pathlib import Path

from sqlalchemy import text
from backend import db

def test_webhook_verify(client, monkeypatch):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "abc")
    rv = client.get("/webhooks/whatsapp/?hub.mode=subscribe&hub.verify_token=abc&hub.challenge=123")
    assert rv.status_code == 200
    assert rv.data == b"123"

def test_webhook_verify_fail(client, monkeypatch):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "abc")
    rv = client.get("/webhooks/whatsapp/?hub.mode=subscribe&hub.verify_token=xyz&hub.challenge=123")
    assert rv.status_code == 403

def test_webhook_receive_dry_run(client, monkeypatch):
    monkeypatch.setenv("WHATSAPP_PROVIDER", "meta")
    monkeypatch.setenv("WHATSAPP_DRY_RUN", "1")
    payload = {
      "entry":[{
          "changes":[{
              "value":{
                  "messages":[{
                      "from":"34600111222",
                      "type":"text",
                      "text":{"body":"hola"}
                  }]
              }
          }]
      }]
    }
    rv = client.post("/webhooks/whatsapp/", data=json.dumps(payload), content_type="application/json")
    assert rv.status_code == 200
    # Here you could also assert that a log was created in the database if you have test db setup

def test_webhook_alias_dry_run_logs_payload(client, monkeypatch):
    monkeypatch.setenv("WHATSAPP_DRY_RUN", "1")
    body = Path("whatsapp_payload.json").read_text(encoding="utf-8")
    with client.application.app_context():
        before = db.session.execute(text("SELECT COUNT(*) FROM whatsapp_message_logs")).scalar()

    rv = client.post("/webhook/whatsapp/", data=body, content_type="application/json")
    assert rv.status_code == 200
    payload = rv.get_json()
    assert payload["ok"] is True
    assert payload["dry_run"] is True

    with client.application.app_context():
        after = db.session.execute(text("SELECT COUNT(*) FROM whatsapp_message_logs")).scalar()
    assert after == before + 1

def test_send_text_dry_run_no_auth(client, monkeypatch):
    monkeypatch.setenv("WHATSAPP_PROVIDER", "meta")
    monkeypatch.setenv("WHATSAPP_DRY_RUN", "1")
    # This test assumes no user is logged in, so it should be redirected to login
    rv = client.post("/notifications/wa_test", json={"to":"34600111222","text":"ping"})
    assert rv.status_code == 302 # Redirect to login page

# To test the authorized endpoint, you would need a fixture to log in a user
# For example:
# def test_send_text_dry_run_admin(admin_client, monkeypatch):
#     monkeypatch.setenv("WHATSAPP_DRY_RUN", "1")
#     rv = admin_client.post("/notifications/wa_test", json={"to":"34600111222","text":"ping"})
#     assert rv.status_code == 200
#     data = rv.get_json()
#     assert data["ok"] is True
#     assert data["dry_run"] is True
