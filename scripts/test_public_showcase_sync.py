#!/usr/bin/env python3
"""
Test public showcase synchronization (4C.1).
Verifies that 4A/4B trust elements (Admin copy calibration, UKK/FAQ, Admin proof image)
are present and correct, while showcase-specific boundaries (no backend, mailto-only contact)
are strictly preserved.

Standard library only.
"""

import hashlib
import os
import re
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXPECTED_WEBP_SHA256 = "837d6db6a6df7ed79ef82611c11f0d174bb78e861961787b6607763fdeda4fe1"


class TestPublicShowcaseSync(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO_ROOT, "index.html"), "r", encoding="utf-8") as f:
            cls.fi_html = f.read()

        with open(os.path.join(REPO_ROOT, "en", "index.html"), "r", encoding="utf-8") as f:
            cls.en_html = f.read()

        with open(os.path.join(REPO_ROOT, "styles", "landing.css"), "r", encoding="utf-8") as f:
            cls.landing_css = f.read()

    def test_01_fi_no_tarjousportaat(self):
        """1. index.html does not contain 'tarjousportaat'."""
        self.assertNotIn("tarjousportaat", self.fi_html)

    def test_02_en_no_counter_offer_steps(self):
        """2. en/index.html does not contain plural 'counter-offer steps'."""
        self.assertNotIn("counter-offer steps", self.en_html)

    def test_03_fi_contains_vastatarjouksen_askeleen(self):
        """3. FI contains 'vastatarjouksen askeleen'."""
        self.assertIn("vastatarjouksen askeleen", self.fi_html)
        self.assertIn("Admin muodostaa autokohtaisen Magic Linkin", self.fi_html)

    def test_04_en_contains_counter_offer_step(self):
        """4. EN contains 'counter-offer step'."""
        self.assertIn("counter-offer step", self.en_html)
        self.assertIn("Admin generates the vehicle-specific magic link", self.en_html)

    def test_05_fi_ukk_has_exactly_five_details(self):
        """5. #ukk contains exactly 5 <details> elements."""
        ukk_match = re.search(r'<section[^>]*id="ukk"[^>]*>([\s\S]*?)</section>', self.fi_html)
        self.assertIsNotNone(ukk_match, "#ukk section must exist")
        details = re.findall(r'<details\b', ukk_match.group(1))
        self.assertEqual(len(details), 5, f"Expected 5 <details> in #ukk, found {len(details)}")
        self.assertIn("Autoliikkeen yleisimmät kysymykset", ukk_match.group(1))

    def test_06_en_faq_has_exactly_five_details(self):
        """6. #faq contains exactly 5 <details> elements."""
        faq_match = re.search(r'<section[^>]*id="faq"[^>]*>([\s\S]*?)</section>', self.en_html)
        self.assertIsNotNone(faq_match, "#faq section must exist")
        details = re.findall(r'<details\b', faq_match.group(1))
        self.assertEqual(len(details), 5, f"Expected 5 <details> in #faq, found {len(details)}")
        self.assertIn("Common questions from dealerships", faq_match.group(1))

    def test_07_ukk_faq_ordering(self):
        """7. UKK/FAQ sections are placed between safety and pilot sections."""
        # FI
        turv_idx = self.fi_html.find('id="turvallisuus"')
        ukk_idx = self.fi_html.find('id="ukk"')
        pilot_idx = self.fi_html.find('id="pilotointi"')

        self.assertGreaterEqual(turv_idx, 0, "FI #turvallisuus must exist")
        self.assertGreaterEqual(ukk_idx, 0, "FI #ukk must exist")
        self.assertGreaterEqual(pilot_idx, 0, "FI #pilotointi must exist")
        self.assertTrue(turv_idx < ukk_idx < pilot_idx, "FI #ukk must be between #turvallisuus and #pilotointi")

        # EN
        safety_idx = self.en_html.find('id="safety"')
        faq_idx = self.en_html.find('id="faq"')
        pilot_en_idx = self.en_html.find('id="pilot"')

        self.assertGreaterEqual(safety_idx, 0, "EN #safety must exist")
        self.assertGreaterEqual(faq_idx, 0, "EN #faq must exist")
        self.assertGreaterEqual(pilot_en_idx, 0, "EN #pilot must exist")
        self.assertTrue(safety_idx < faq_idx < pilot_en_idx, "EN #faq must be between #safety and #pilot")

    def test_08_admin_webp_exists_on_disk(self):
        """8. Admin WebP asset exists on disk, is non-empty, and matches expected SHA256."""
        webp_path = os.path.join(REPO_ROOT, "assets", "kopilotti-admin-pricing-demo-2026-09.webp")
        self.assertTrue(os.path.isfile(webp_path), "Admin WebP asset file must exist")
        size = os.path.getsize(webp_path)
        self.assertGreater(size, 40000, "Admin WebP asset should be roughly 54-55 KB")

        with open(webp_path, "rb") as f:
            actual_sha256 = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(actual_sha256, EXPECTED_WEBP_SHA256, "WebP SHA256 must match production asset exactly")

    def test_09_fi_and_en_reference_webp(self):
        """9. Both FI and EN refer to the WebP asset."""
        self.assertIn("assets/kopilotti-admin-pricing-demo-2026-09.webp", self.fi_html)
        self.assertIn("assets/kopilotti-admin-pricing-demo-2026-09.webp", self.en_html)

    def test_10_alt_texts_exist(self):
        """10. Alt texts exist on both FI and EN images."""
        self.assertIn('alt="Kopilotti Adminin hinnoittelunäkymä synteettisillä esimerkkitiedoilla.', self.fi_html)
        self.assertIn('alt="Kopilotti Admin pricing view with synthetic example data,', self.en_html)

    def test_11_captions_state_synthetic_data(self):
        """11. Captions state synthetic data clearly."""
        self.assertIn("Kopilotti Adminin hinnoittelunäkymä (synteettiset esimerkkitiedot, DEMO-006 / esimerkkiajoneuvo).", self.fi_html)
        self.assertIn("Admin interface shown in Finnish. Synthetic example data (DEMO-006 / example vehicle).", self.en_html)

    def test_12_mailto_links_retained(self):
        """12. Both index.html and en/index.html still retain mailto:hello@kopilotti.online."""
        self.assertIn("mailto:hello@kopilotti.online", self.fi_html)
        self.assertIn("mailto:hello@kopilotti.online", self.en_html)

    def test_13_no_api_contact_or_backend_csrf(self):
        """13. Neither page contains /api/contact, data-contact-form, or csrf."""
        for name, html in [("index.html", self.fi_html), ("en/index.html", self.en_html)]:
            self.assertNotIn("/api/contact", html, f"{name} must not reference /api/contact")
            self.assertNotIn("data-contact-form", html, f"{name} must not have contact form markup")
            self.assertNotIn("csrf", html.lower(), f"{name} must not contain csrf references")

    def test_14_no_js_file_added_for_faq(self):
        """14. No new JavaScript file added for FAQ/UKK."""
        self.assertIsNone(re.search(r'<script[^>]*src="[^"]*(faq|ukk)[^"]*"', self.fi_html, re.I))
        self.assertIsNone(re.search(r'<script[^>]*src="[^"]*(faq|ukk)[^"]*"', self.en_html, re.I))

    def test_15_css_responsive_properties(self):
        """15. Admin proof image CSS contains max-width: 100% and height: auto."""
        self.assertIn(".admin-proof-image", self.landing_css)
        img_rule_match = re.search(r'\.admin-proof-image\s*\{([^}]*)\}', self.landing_css)
        self.assertIsNotNone(img_rule_match, ".admin-proof-image rule must exist")
        rule_content = img_rule_match.group(1)
        self.assertIn("max-width: 100%", rule_content)
        self.assertIn("height: auto", rule_content)


if __name__ == "__main__":
    unittest.main()
