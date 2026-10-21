import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from account_client import AccountClient, AccountError, validate_server_url, validate_checkout_url
from account_ui import AccountMixin
import test_app
import app as service

class AccessTests(unittest.TestCase):
    setUp = test_app.SubscriptionServiceTests.setUp
    tearDown = test_app.SubscriptionServiceTests.tearDown
    register = test_app.SubscriptionServiceTests.register
    def test_access_free_premium_and_unknown(self):
        self.assertEqual(self.client.post('/api/access', json={'mission': 'drive'}).status_code, 401)
        token = self.register()
        headers = {'Authorization': f'Bearer {token}'}
        for mission in ('led', 'motor', 'button_led', 'traffic', 'crossing', 'light'):
            self.assertTrue(self.client.post('/api/access', headers=headers, json={'mission': mission}).get_json()['allowed'])
        for mission in ('drive', 'obstacle', 'free'):
            self.assertFalse(self.client.post('/api/access', headers=headers, json={'mission': mission}).get_json()['allowed'])
        self.assertFalse(self.client.post('/api/access', headers=headers, json={'mission': 'led', 'challenge': True}).get_json()['allowed'])
        self.assertEqual(self.client.post('/api/access', headers=headers, json={'mission': 'unknown'}).status_code, 400)

    def test_sync_unlocks_and_cancelled_locks(self):
        token = self.register()
        headers = {'Authorization': f'Bearer {token}'}
        with service.db_connect() as db:
            db.execute("INSERT INTO subscriptions(user_id,mp_id,status,payer_email) VALUES (1,'sub1','pending','payer@example.com')")
        data = {'id': 'sub1', 'status': 'authorized', 'external_reference': 'playrobot-user-1'}
        with patch.object(service, 'mp_request', return_value=data):
            response = self.client.post('/api/billing/sync', headers=headers)
        self.assertTrue(response.get_json()['premium'])
        self.assertTrue(self.client.post('/api/access', headers=headers, json={'mission': 'drive'}).get_json()['allowed'])
        self.assertEqual(self.client.post('/api/billing/checkout', headers=headers, json={}).status_code, 409)
        data['status'] = 'cancelled'
        with patch.object(service, 'mp_request', return_value=data):
            response = self.client.post('/api/billing/sync', headers=headers)
        self.assertFalse(response.get_json()['premium'])
        self.assertFalse(self.client.post('/api/access', headers=headers, json={'mission': 'drive'}).get_json()['allowed'])

    def test_sync_rejects_other_owner(self):
        token = self.register()
        with service.db_connect() as db:
            db.execute("INSERT INTO subscriptions(user_id,mp_id,status,payer_email) VALUES (1,'sub1','pending','payer@example.com')")
        data = {'id': 'sub1', 'status': 'authorized', 'external_reference': 'playrobot-user-99'}
        with patch.object(service, 'mp_request', return_value=data):
            response = self.client.post('/api/billing/sync', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, 502)
        self.assertFalse(service.subscription_is_active(1))

    def test_sync_cannot_consult_other_users_subscription(self):
        token = self.register()
        self.client.post('/api/auth/register', json={'email': 'other@example.com', 'password': 'otra-clave-larga-2026'})
        with service.db_connect() as db:
            db.execute("INSERT INTO subscriptions(user_id,mp_id,status,payer_email) VALUES (2,'other-sub','pending','payer@example.com')")
        with patch.object(service, 'mp_request') as api:
            response = self.client.post('/api/billing/sync', headers={'Authorization': f'Bearer {token}'})
        api.assert_not_called()
        self.assertFalse(response.get_json()['premium'])

class ClientTests(unittest.TestCase):
    def test_server_url(self):
        self.assertEqual(validate_server_url(' http://127.0.0.1:8001/ '), 'http://127.0.0.1:8001')
        self.assertTrue(validate_server_url('https://school.example'))
        for url in ('http://school.example', 'https://user:secret@school.example', 'https://school.example?key=secret', 'file:///etc/passwd', 'https://[bad', 12):
            with self.assertRaises(AccountError): validate_server_url(url)

    def test_checkout_url(self):
        self.assertTrue(validate_checkout_url('https://www.mercadopago.com.mx/subscriptions/checkout?id=abc'))
        for url in ('http://www.mercadopago.com.mx', 'https://www.mercadopago.com.mx.evil.example', 'file:///tmp/unsafe'):
            with self.assertRaises(AccountError): validate_checkout_url(url)

    def test_utf8_login_and_session_header(self):
        client = AccountClient('http://127.0.0.1:8001')
        client.token = 'session-token'
        with patch.object(client.opener, 'open') as opening:
            opening.return_value.__enter__.return_value.read.return_value = b'{"ok":true}'
            self.assertTrue(client.request('POST', '/api/auth/login', {'password': 'contraseña'})['ok'])
        request = opening.call_args.args[0]
        self.assertEqual(request.get_header('Authorization'), 'Bearer session-token')
        self.assertIn('contraseña', request.data.decode('utf-8'))

    def test_network_and_auth_errors(self):
        client = AccountClient('http://127.0.0.1:8001')
        error = HTTPError('http://localhost', 401, 'Unauthorized', {}, io.BytesIO(b'{"error":"Inicia sesion"}'))
        with patch.object(client.opener, 'open', side_effect=error):
            with self.assertRaises(AccountError) as caught: client.request('GET', '/api/me')
        self.assertEqual(caught.exception.status, 401)
        with patch.object(client.opener, 'open', side_effect=URLError('offline')):
            with self.assertRaises(AccountError): client.request('GET', '/api/me')

    def test_free_policy(self):
        for mission in ('led', 'motor', 'button_led', 'traffic', 'crossing', 'light'):
            self.assertTrue(AccountMixin._mission_is_free(mission))
            self.assertFalse(AccountMixin._mission_is_free(mission, {'number': 9}))
        for mission in ('drive', 'obstacle', 'free', 'unknown'):
            self.assertFalse(AccountMixin._mission_is_free(mission))
