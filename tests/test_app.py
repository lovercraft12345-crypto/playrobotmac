import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as service


class SubscriptionServiceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        service.DB_PATH = Path(self.tempdir.name) / "test.db"
        service.init_db()
        service.app.config["TESTING"] = True
        service.limiter.enabled = False
        self.client = service.app.test_client()

    def tearDown(self):
        self.tempdir.cleanup()

    def register(self):
        response = self.client.post("/api/auth/register", json={
            "email": "Tutor@Example.com",
            "password": "clave-segura-larga-2026",
        })
        self.assertEqual(response.status_code, 201)
        return response.get_json()["token"]

    def test_register_and_free_levels(self):
        token = self.register()
        response = self.client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["premium"])
        self.assertEqual(response.get_json()["free_levels"], 6)

    def test_weak_password_is_rejected(self):
        response = self.client.post("/api/auth/register", json={
            "email": "tutor@example.com", "password": "corta",
        })
        self.assertEqual(response.status_code, 400)

    def test_auth_required_for_account_status(self):
        response = self.client.get("/api/me")
        self.assertEqual(response.status_code, 401)

    def test_webhook_hmac_verification(self):
        secret, data_id, request_id, timestamp = "test-secret", "abc123", "req-123", "1720000000"
        manifest = f"id:{data_id.lower()};request-id:{request_id};ts:{timestamp};"
        digest = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
        signature = f"ts={timestamp},v1={digest}"
        self.assertTrue(service.verify_webhook_signature(data_id, signature, request_id, secret))
        self.assertFalse(service.verify_webhook_signature(data_id, signature, "wrong", secret))

    def test_checkout_needs_access_token_and_public_url(self):
        token = self.register()
        with patch.dict("os.environ", {"MP_ACCESS_TOKEN": "", "PUBLIC_BASE_URL": ""}):
            response = self.client.post("/api/billing/checkout", json={}, headers={
                "Authorization": f"Bearer {token}",
            })
        self.assertEqual(response.status_code, 503)

    def test_checkout_creates_pending_subscription_and_returns_hosted_url(self):
        token = self.register()
        with patch.dict("os.environ", {
            "MP_ACCESS_TOKEN": "TEST-test-token",
            "PUBLIC_BASE_URL": "https://playrobot-test.trycloudflare.com",
            "PREMIUM_MONTHLY_PRICE_MXN": "99",
        }), patch.object(service, "mp_request", return_value={
            "id": "preapproval-123",
            "status": "pending",
            "init_point": "https://www.mercadopago.com.mx/subscriptions/checkout/test",
        }) as mp_call:
            response = self.client.post("/api/billing/checkout", json={}, headers={
                "Authorization": f"Bearer {token}",
            })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["status"], "pending")
        self.assertTrue(response.get_json()["checkout_url"].startswith("https://"))
        self.assertEqual(mp_call.call_args.args[:2], ("POST", "/preapproval"))
        with service.db_connect() as conn:
            row = conn.execute("SELECT status FROM subscriptions WHERE mp_id='preapproval-123'").fetchone()
        self.assertEqual(row["status"], "pending")


if __name__ == "__main__":
    unittest.main()
