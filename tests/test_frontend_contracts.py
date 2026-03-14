import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ADMIN_HTML = ROOT / "landing" / "admin.html"


class AdminFrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = ADMIN_HTML.read_text(encoding="utf-8")

    def test_admin_page_uses_cookie_session_login(self):
        self.assertIn("/v1/admin/session", self.html)
        self.assertIn("credentials: 'same-origin'", self.html)
        self.assertIn("Access Dashboard", self.html)

    def test_admin_page_wires_risk_profile_endpoints(self):
        self.assertIn("/v1/admin/risk-config/${selectedRiskEmail}", self.html)
        self.assertIn("/v1/admin/risk-config-history/${email}", self.html)
        self.assertIn("configHistory", self.html)
        self.assertIn("Reset To Defaults", self.html)

    def test_admin_page_wires_explain_and_purge_actions(self):
        self.assertIn("/v1/explain/${riskId}", self.html)
        self.assertIn("/v1/admin/user/${email}", self.html)
        self.assertIn("confirmPurge", self.html)
        self.assertIn("openConfigModal", self.html)

    def test_admin_page_shows_masked_key_and_risk_badges(self):
        self.assertIn("api_key_preview", self.html)
        self.assertIn("Custom Risk", self.html)
        self.assertIn("Default Risk", self.html)


if __name__ == "__main__":
    unittest.main()
