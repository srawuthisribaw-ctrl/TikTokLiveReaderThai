import unittest
from core.i18n import set_language, get_language, tr, TRANSLATIONS

class TestI18n(unittest.TestCase):
    def setUp(self):
        # Save current language to restore later
        self.original_lang = get_language()

    def tearDown(self):
        # Restore original language
        set_language(self.original_lang)

    def test_default_language(self):
        # Check that default language is either th or en
        self.assertIn(get_language(), ["th", "en"])

    def test_set_language(self):
        set_language("en")
        self.assertEqual(get_language(), "en")
        set_language("th")
        self.assertEqual(get_language(), "th")
        # Test invalid language setting (should ignore)
        set_language("fr")
        self.assertEqual(get_language(), "th")

    def test_translation_switching(self):
        set_language("th")
        th_val = tr("WELCOME_MSG")
        self.assertEqual(th_val, "ยินดีต้อนรับสู่ ติ๊กต็อก ไลฟ์ รีดเดอร์ พร้อมใช้งานค่ะ")

        set_language("en")
        en_val = tr("WELCOME_MSG")
        self.assertEqual(en_val, "Welcome to TikTok Live Reader. System is ready to use.")

    def test_translation_fallback(self):
        set_language("en")
        # Key does not exist, should return key itself
        self.assertEqual(tr("NON_EXISTENT_KEY"), "NON_EXISTENT_KEY")
        # Key does not exist, should return custom default
        self.assertEqual(tr("NON_EXISTENT_KEY", "Default Val"), "Default Val")

    def test_translations_keys_alignment(self):
        # Verify both th and en have identical keys
        th_keys = set(TRANSLATIONS["th"].keys())
        en_keys = set(TRANSLATIONS["en"].keys())
        
        missing_in_en = th_keys - en_keys
        missing_in_th = en_keys - th_keys

        self.assertEqual(len(missing_in_en), 0, f"Keys present in th but missing in en: {missing_in_en}")
        self.assertEqual(len(missing_in_th), 0, f"Keys present in en but missing in th: {missing_in_th}")

if __name__ == "__main__":
    unittest.main()
