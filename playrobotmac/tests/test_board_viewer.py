import tempfile
import unittest
from pathlib import Path
import numpy as np
from board_viewer import BoardModel


class BoardModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = BoardModel(Path(__file__).resolve().parents[1] / 'assets/models/playrobot.3ds')

    def test_export_has_all_objects_and_valid_faces(self):
        self.assertEqual(len(self.model.object_names), 73)
        self.assertEqual(len(self.model.faces), 173398)
        self.assertTrue(np.isfinite(self.model.vertices).all())
        self.assertLess(int(self.model.faces.max()), len(self.model.vertices))
        self.assertGreater(len(np.unique(self.model.colors, axis=0)), 10)

    def test_rotation_and_zoom_change_render(self):
        model = self.model
        initial = np.asarray(model.render(240, 180))
        rotated = np.asarray(model.render(240, 180, yaw=0.8))
        enlarged = np.asarray(model.render(240, 180, zoom=1.7))
        background = np.array([234, 240, 246])
        self.assertGreater(np.count_nonzero(np.any(initial != rotated, axis=2)), 1000)
        self.assertGreater(np.count_nonzero(np.any(enlarged != background, axis=2)),
                           np.count_nonzero(np.any(initial != background, axis=2)))

    def test_invalid_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.3ds'
            path.write_bytes(b'not a model')
            with self.assertRaises(ValueError):
                BoardModel(path)
