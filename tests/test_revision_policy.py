import unittest

from app.tools.revision_policy import normalize_paragraph


class TestNormalizeParagraph(unittest.TestCase):
    def test_no_change_returns_empty_reasons(self):
        text = "你好，世界。"
        revised, reasons = normalize_paragraph(text)
        self.assertEqual(revised, text)
        self.assertEqual(reasons, [])

    def test_collapse_extra_spaces_between_words(self):
        text = "Hello  world"
        revised, reasons = normalize_paragraph(text)
        self.assertEqual(revised, "Hello world")
        self.assertIn("合并多余空格", reasons)

    def test_preserve_leading_and_trailing_whitespace(self):
        text = "  Hello  world  "
        revised, reasons = normalize_paragraph(text)
        self.assertEqual(revised, "  Hello world  ")
        self.assertIn("合并多余空格", reasons)

    def test_remove_space_before_punctuation(self):
        text = "你好 ，世界。"
        revised, reasons = normalize_paragraph(text)
        self.assertEqual(revised, "你好，世界。")
        self.assertIn("删除标点前空格", reasons)

    def test_collapse_duplicate_punctuation(self):
        text = "你好！！"
        revised, reasons = normalize_paragraph(text)
        self.assertEqual(revised, "你好！")
        self.assertIn("合并重复标点", reasons)


if __name__ == "__main__":
    unittest.main()

