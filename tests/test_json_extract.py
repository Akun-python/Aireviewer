import unittest

from app.tools.json_extract import extract_json_list, extract_json_object


class TestJsonExtract(unittest.TestCase):
    def test_extract_list_direct(self):
        self.assertEqual(extract_json_list('[{"a": 1}]'), [{"a": 1}])

    def test_extract_list_with_noise(self):
        text = "前缀\n```json\n[{\"a\": 1}]\n```\n后缀"
        self.assertEqual(extract_json_list(text), [{"a": 1}])

    def test_extract_object_direct(self):
        self.assertEqual(extract_json_object('{"a": 1}'), {"a": 1})

    def test_extract_object_with_noise(self):
        text = "prefix {\"a\": 1} suffix"
        self.assertEqual(extract_json_object(text), {"a": 1})

    def test_missing_returns_none(self):
        self.assertIsNone(extract_json_list("no json here"))
        self.assertIsNone(extract_json_object("no json here"))


if __name__ == "__main__":
    unittest.main()

