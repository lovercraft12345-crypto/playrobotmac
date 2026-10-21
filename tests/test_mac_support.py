import importlib.util
from pathlib import Path
from unittest.mock import patch
import unittest
from macos_voice import spanish_voice

class MacTests(unittest.TestCase):
    def test_voice_never_defaults_to_english(self):
        self.assertIsNone(spanish_voice('Samantha en_US # Hello'))
        text='Samantha en_US # Hello\nJorge es_ES # Hola\nPaulina es_MX # Hola'
        self.assertEqual(spanish_voice(text),'Paulina')
        self.assertEqual(spanish_voice('Mónica es_ES # Hola'),'Mónica')

    def test_frozen_usb_dispatch_does_not_open_gui(self):
        spec=importlib.util.spec_from_file_location('mac_entry',Path(__file__).parents[1]/'macos/entry.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        with patch.object(mod.sys,'argv',['PlayRobot','-m','mpremote','connect','/dev/cu.test']),patch.object(mod.runpy,'run_module') as run:
            mod.main()
            run.assert_called_once_with('mpremote',run_name='__main__')
        with patch.object(mod.sys,'argv',['PlayRobot','-m','os']):
            with self.assertRaises(SystemExit):mod.main()
