"""Run on Windows: python -m unittest test_helper.py."""
import importlib.util
import json
from pathlib import Path
from queue import Queue
import tempfile
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('helper', Path(__file__).with_name('soundboard-ptt.py'))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

class LoginTests(unittest.TestCase):
    def test_retry_reopens_pending_browser_page(self):
        app = helper.Helper.__new__(helper.Helper)
        app.busy = True
        app.base = 'https://example.test'
        app.login_path = '/auth/discord?request=abc'
        with patch.object(helper.webbrowser, 'open') as browser:
            app.login()
            browser.assert_called_once_with(app.base + app.login_path)

    def test_windows_encryption_roundtrip(self):
        original = b'secret-helper-credential'
        encrypted = helper.protect_login(original)
        self.assertNotIn(original, encrypted)
        self.assertEqual(helper.protect_login(encrypted, decrypt=True), original)

    def test_saved_login_restores_after_reopening(self):
        with tempfile.TemporaryDirectory() as directory:
            app = helper.Helper.__new__(helper.Helper)
            app.base = 'https://example.test'
            app.token = 'a' * 64
            app.login_file = Path(directory) / 'helper-login.json'
            app.status = Mock()
            app.save_login()
            saved = app.login_file.read_text()
            self.assertNotIn(app.token, saved)
            self.assertIn('encrypted', json.loads(saved))
            reopened = helper.Helper.__new__(helper.Helper)
            reopened.login_file = app.login_file
            reopened.url = Mock()
            reopened.status = Mock()
            reopened.messages = Queue()
            reopened.login_generation = 0
            reopened.request = Mock(return_value={'devices':[]})
            class ImmediateThread:
                def __init__(self, target, **kwargs): self.target = target
                def start(self): self.target()
            with patch.object(helper.threading, 'Thread', ImmediateThread):
                reopened.restore_login()
            reopened.request.assert_called_once_with(app.base, '/api/helper/devices', app.token)
            self.assertEqual(reopened.messages.get_nowait(), ('login', 0, app.base, app.token, []))

if __name__ == '__main__': unittest.main()
