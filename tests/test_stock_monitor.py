import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.stock_monitor import evaluate


class StockMonitorTests(unittest.TestCase):
    def test_triggered_when_move_and_volume_ratio_both_hit(self):
        quote = {
            "code": "601619",
            "name": "嘉泽新能",
            "price": 5.59,
            "pre_close": 5.21,
            "change_pct": 7.29,
            "volume_lots": 100000,
            "bid1": 5.58,
            "ask1": 5.59,
            "bid1_vol_lots": 36300,
            "ask1_vol_lots": 187900,
            "updated_at": "2026-04-13 11:09:37",
        }
        result = evaluate(quote, 2.0, 1.5)
        self.assertTrue(result["triggered"])

    def test_reseal_analysis_high_probability(self):
        from tools.stock_monitor import analyze_reseal

        quote = {
            "code": "601619",
            "name": "嘉泽新能",
            "price": 10.85,
            "pre_close": 9.86,
            "high": 10.85,
            "low": 10.12,
            "bid1": 10.84,
            "ask1": 10.85,
            "bid1_vol_lots": 500000,
            "ask1_vol_lots": 80000,
            "change_pct": 10.04,
            "volume_lots": 800000,
            "updated_at": "2026-04-13 10:45:00",
        }
        result = analyze_reseal(quote)
        self.assertEqual(result["verdict"], "回封概率高")


if __name__ == "__main__":
    unittest.main()
