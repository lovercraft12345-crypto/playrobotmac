import unittest
from unittest.mock import Mock
from account_client import AccountClient, AccountError

class DemoAdminTests(unittest.TestCase):
    def test_demo_access_is_offline_and_premium(self):
        client = AccountClient('http://127.0.0.1:8001')
        client.opener.open = Mock(side_effect=AssertionError('No debe usar red'))
        self.assertTrue(client.login_demo_admin('admin', 'admin'))
        self.assertTrue(client.request('GET', '/api/me')['premium'])
        for mission in ('drive', 'obstacle', 'free'):
            self.assertTrue(client.request('POST', '/api/access', {'mission': mission})['allowed'])
        self.assertTrue(client.request('POST', '/api/billing/sync')['premium'])
        with self.assertRaises(AccountError):
            client.request('POST', '/api/billing/checkout', {})
        client.opener.open.assert_not_called()

    def test_wrong_password_does_not_create_session(self):
        client = AccountClient('http://127.0.0.1:8001')
        self.assertFalse(client.login_demo_admin('admin', 'incorrecta'))
        self.assertEqual(client.token, '')

    def test_logout_restores_server_requests(self):
        client = AccountClient('http://127.0.0.1:8001')
        client.login_demo_admin('admin', 'admin')
        client.token = ''
        client.opener.open = Mock(side_effect=OSError('sin servidor'))
        with self.assertRaises(AccountError):
            client.request('GET', '/api/me')
        client.opener.open.assert_called_once()
