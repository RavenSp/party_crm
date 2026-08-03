from django.test import SimpleTestCase

from helpers.common import name_normalizer


class NameNormalizerTests(SimpleTestCase):
    """Тесты нормализации имён."""

    def test_removes_spaces(self):
        self.assertEqual(name_normalizer('Иванов Иван Иванович'), 'ивановиваниванович')

    def test_removes_special_characters(self):
        self.assertEqual(name_normalizer('а.,:!?%_-*'), 'а')

    def test_lowercases(self):
        self.assertEqual(name_normalizer('ИВАНОВ'), 'иванов')

    def test_combined(self):
        self.assertEqual(name_normalizer('Иванов, Иван. Иванович!'), 'ивановиваниванович')

    def test_empty_string(self):
        self.assertEqual(name_normalizer(''), '')
