"""Check the entry gate without requiring a graphical display."""
import unittest
import queue
from types import SimpleNamespace
from unittest.mock import Mock
from account_ui import AccountMixin


class EntryTests(unittest.TestCase):
    def test_old_request_does_not_clear_busy_state_of_new_session(self):
        callback = Mock()
        pending = queue.Queue()
        pending.put((3, callback, {}, None))
        app = SimpleNamespace(_account_queue=pending, _account_generation=4,
                              _account_busy=True, after=Mock(), _drain_account_queue=Mock())
        AccountMixin._drain_account_queue(app)
        self.assertTrue(app._account_busy)
        callback.assert_not_called()

    def test_logout_clears_pending_ui_state(self):
        app = SimpleNamespace(_account_generation=3, _account_busy=True,
            account_client=SimpleNamespace(token='fake'), account_info={'premium': True},
            _checkout_url='fake', _account_poll_id=None, on_home_screen=True,
            _paint_account=Mock(), _set_account_message=Mock())
        AccountMixin._account_logout(app)
        self.assertFalse(app._account_busy)
        self.assertEqual(app.account_client.token, '')
        self.assertEqual(app._account_generation, 4)

    def make_app(self):
        app = SimpleNamespace(_workshop_started=False, account_window=None)
        for name in ('_build_start_screen', 'deiconify', '_update_lesly_tips', 'lift', 'destroy'):
            setattr(app, name, Mock())
        app._close_account_panel = lambda: AccountMixin._close_account_panel(app)
        return app

    def test_guest_opens_workshop_once(self):
        app = self.make_app()
        AccountMixin._enter_workshop(app)
        AccountMixin._enter_workshop(app)
        app._build_start_screen.assert_called_once()
        app.deiconify.assert_called_once()
        app.destroy.assert_not_called()

    def test_close_initial_gate_quits(self):
        app = self.make_app()
        app._close_account_panel()
        app.destroy.assert_called_once()
        app._build_start_screen.assert_not_called()

    def test_verified_account_opens_after_profile(self):
        app = self.make_app()
        app.account_client = SimpleNamespace(token='test-session')
        app._paint_account = Mock()
        app._set_account_message = Mock()
        app._enter_workshop = Mock()
        pending = []
        app._account_async = lambda operation, callback, message: pending.append(callback)
        AccountMixin._refresh_account(app, enter_workshop=True)
        app._enter_workshop.assert_not_called()
        pending[0]({'premium': True})
        app._enter_workshop.assert_called_once()
        self.assertTrue(app.account_info['premium'])
