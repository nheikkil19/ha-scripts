import unittest
import sys
import os

sys.path.append(os.path.dirname(__file__) + "/../")
from programs import TotalCheapest, Sections

class TotalCheapestTests(unittest.TestCase):
    def test_evaluate_returns_correct_result(self):
        prices = [10, 20, 30, 40, 50]
        n = 3
        program = TotalCheapest(prices, n)
        result = program.evaluate()
        expected_result = ([True, True, True, False, False], 60)
        self.assertEqual(result, expected_result)

    def test_evaluate_handles_empty_prices_list(self):
        prices = []
        n = 3
        program = TotalCheapest(prices, n)
        result = program.evaluate()
        expected_result = ([], 0)
        self.assertEqual(result, expected_result)


class SectionsTests(unittest.TestCase):
    def test_evaluate_returns_correct_result(self):
        prices = [10, 20, 30, 40, 50]
        section_lengths = [2, 3]
        on_hours = [1, 4]
        program = Sections(prices, section_lengths, on_hours)
        result = program.evaluate()
        expected_result = ([True, False, True, True, True], 130)
        self.assertEqual(result, expected_result)

    def test_evaluate_handles_empty_prices_list(self):
        prices = []
        section_lengths = [2, 3]
        on_hours = [1, 4]
        with self.assertRaises(ValueError):
            program = Sections(prices, section_lengths, on_hours)
            program.evaluate()

if __name__ == "__main__":
    unittest.main()
