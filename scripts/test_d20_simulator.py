from pathlib import Path
import unittest


HTML_PATH = Path(__file__).resolve().parents[1] / "d20-simulator.html"


class D20SimulatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""
        cls.lower = cls.html.lower()

    def test_is_one_offline_file(self):
        self.assertNotIn("<script src=", self.lower)
        self.assertNotIn("<link ", self.lower)
        self.assertNotIn("http://", self.lower)
        self.assertNotIn("https://", self.lower)

    def test_has_accessible_controls(self):
        self.assertTrue(HTML_PATH.exists(), "d20-simulator.html must exist")
        self.assertIn('type="button"', self.lower)
        self.assertIn('id="roll-button"', self.lower)
        self.assertIn('aria-live="polite"', self.lower)
        self.assertIn(":focus-visible", self.lower)

    def test_has_required_roll_contract(self):
        self.assertIn("crypto.getrandomvalues", self.lower)
        self.assertIn("4294967280", self.html)
        self.assertIn('event.code === "Space"', self.html)
        self.assertIn("slice(0, 8)", self.html)
        self.assertIn("prefers-reduced-motion", self.lower)
        self.assertIn("if (rolling) return", self.html)


if __name__ == "__main__":
    unittest.main()
