import copy
import json
import unittest
from modern_ui import validate_project


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.project = {'format': 'playrobot-project', 'version': 1, 'mission': 'led',
            'challenge': None, 'program': {'steps': ['start', 'led', 'wait', 'off', 'repeat'],
            'parameters': [0, 5, 2, 5, 3], 'loose_steps': ['wait'],
            'loose_parameters': [1], 'loose_positions': [[200, 150]]}}

    def test_round_trip_preserves_individual_pins_and_loose_gears(self):
        encoded = json.dumps(self.project)
        self.assertEqual(validate_project(json.loads(encoded)), self.project)

    def test_unknown_gears_are_rejected(self):
        self.project['program']['steps'][1] = 'python_eval'
        with self.assertRaises(ValueError):
            validate_project(self.project)

    def test_truncated_parameter_lists_are_rejected(self):
        self.project['program']['parameters'].pop()
        with self.assertRaises(ValueError):
            validate_project(self.project)

    def test_nonfinite_positions_are_rejected(self):
        self.project['program']['loose_positions'] = [[float('nan'), 1]]
        with self.assertRaises(ValueError):
            validate_project(self.project)

    def test_import_drops_unrecognized_program_fields(self):
        self.project['program']['account_info'] = {'premium': True}
        validated = validate_project(copy.deepcopy(self.project))
        self.assertNotIn('account_info', validated['program'])
