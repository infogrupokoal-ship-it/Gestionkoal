import hmac
import hashlib
import json


def sign_body(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_webhook_signature_valid(client, monkeypatch):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "s3cr3t")
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"id": "wamid.1", "from": "34600111222", "type": "text", "text": {"body": "hola"}}
                            ]
                        }
                    }
                ]
            }
        ]
    }
    body = json.dumps(payload).encode("utf-8")
    sig = sign_body("s3cr3t", body)
    rv = client.post(
        "/webhooks/whatsapp/",
        data=body,
        content_type="application/json",
        headers={"X-Hub-Signature-256": sig},
    )
    assert rv.status_code == 200


def test_webhook_signature_invalid(client, monkeypatch):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "s3cr3t")
    payload = {"entry": [{"changes": [{"value": {"messages": []}}]}]}
    body = json.dumps(payload).encode("utf-8")
    rv = client.post(
        "/webhooks/whatsapp/",
        data=body,
        content_type="application/json",
        headers={"X-Hub-Signature-256": "sha256=deadbeef"},
    )
    assert rv.status_code == 401


def test_webhook_idempotent_duplicate(client, monkeypatch):
    monkeypatch.setenv("WHATSAPP_DRY_RUN", "1")
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"id": "wamid.dup", "from": "34600111222", "type": "text", "text": {"body": "hola"}}
                            ]
                        }
                    }
                ]
            }
        ]
    }
    body = json.dumps(payload).encode("utf-8")
    rv1 = client.post("/webhooks/whatsapp/", data=body, content_type="application/json")
    assert rv1.status_code == 200
    rv2 = client.post("/webhooks/whatsapp/", data=body, content_type="application/json")
    assert rv2.status_code == 200
    data = rv2.get_json()
    assert data.get("duplicate") is True

