import unittest
from datetime import date
import pandas as pd
from gallery_inspector.generate import _extract_year_month

class TestGenerate(unittest.TestCase):
    def test_extract_year_month_valid_date(self):
        y, m = _extract_year_month(date(2026, 6, 7))
        self.assertEqual(y, "2026")
        self.assertEqual(m, "06")

    def test_extract_year_month_string_colon(self):
        y, m = _extract_year_month("2026:06:07 12:00:00")
        self.assertEqual(y, "2026")
        self.assertEqual(m, "06")

    def test_extract_year_month_string_dash(self):
        y, m = _extract_year_month("2026-06-07")
        self.assertEqual(y, "2026")
        self.assertEqual(m, "06")

    def test_extract_year_month_none(self):
        y, m = _extract_year_month(None)
        self.assertIsNone(y)
        self.assertIsNone(m)

    def test_extract_year_month_pandas_nat(self):
        y, m = _extract_year_month(pd.NaT)
        self.assertIsNone(y)
        self.assertIsNone(m)

    def test_extract_year_month_float_nan(self):
        y, m = _extract_year_month(float("nan"))
        self.assertIsNone(y)
        self.assertIsNone(m)
