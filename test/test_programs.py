import os
import sys
import unittest

sys.path.append(os.path.dirname(__file__) + "/../")
from programs import Sections, TotalCheapest  # noqa: E402


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

    def test_name_returns_correct_name(self):
        prices = [10, 20, 30, 40, 50]
        n = 3
        program = TotalCheapest(prices, n)
        result = program.name
        expected_result = "Total cheapest"
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

    def test_name_returns_correct_name(self):
        prices = [10, 20, 30, 40, 50]
        section_lengths = [2, 3]
        on_hours = [1, 4]
        program = Sections(prices, section_lengths, on_hours)
        result = program.name
        expected_result = "1/2, 4/3"
        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
