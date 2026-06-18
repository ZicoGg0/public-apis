# -*- coding: utf-8 -*-

import unittest

from validate.utils import (
    error_message,
    check_field_value,
    read_file_lines,
    read_file_content,
    is_category_header,
    is_table_entry,
)


class TestValidateUtils(unittest.TestCase):

    def test_error_message_format(self):
        result = error_message(0, 'test error')
        self.assertEqual(result, '(L001) test error')

        result = error_message(9, 'another error')
        self.assertEqual(result, '(L010) another error')

        result = error_message(99, 'error')
        self.assertEqual(result, '(L100) error')

    def test_check_field_value_with_valid_value(self):
        valid_values = ['Yes', 'No', 'Unknown']

        for value in valid_values:
            with self.subTest(value=value):
                err_msgs = check_field_value(0, value, valid_values, 'TestField')
                self.assertIsInstance(err_msgs, list)
                self.assertEqual(len(err_msgs), 0)

    def test_check_field_value_with_invalid_value(self):
        valid_values = ['Yes', 'No']

        err_msgs = check_field_value(0, 'Maybe', valid_values, 'HTTPS')
        self.assertIsInstance(err_msgs, list)
        self.assertEqual(len(err_msgs), 1)
        self.assertEqual(err_msgs[0], '(L001) Maybe is not a valid HTTPS option')

    def test_check_field_value_preserves_line_number(self):
        err_msgs = check_field_value(5, 'invalid', ['valid'], 'Field')
        self.assertEqual(err_msgs[0], '(L006) invalid is not a valid Field option')

    def test_is_category_header(self):
        self.assertTrue(is_category_header('### Animals', '###'))
        self.assertTrue(is_category_header('### ', '###'))
        self.assertFalse(is_category_header('## Index', '###'))
        self.assertFalse(is_category_header('| data |', '###'))
        self.assertFalse(is_category_header('', '###'))

    def test_is_table_entry(self):
        self.assertTrue(is_table_entry('| [API](http://ex.com) | Desc | No | Yes | Yes |'))
        self.assertFalse(is_table_entry('|---|---|---|'))
        self.assertFalse(is_table_entry('### Category'))
        self.assertFalse(is_table_entry(''))
        self.assertFalse(is_table_entry('Some text'))

    def test_read_file_lines(self):
        import tempfile
        import os

        content = 'line1\nline2\nline3'
        fd, path = tempfile.mkstemp(suffix='.txt')
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(content)
            lines = read_file_lines(path)
            self.assertEqual(lines, ['line1', 'line2', 'line3'])
        finally:
            os.unlink(path)

    def test_read_file_content(self):
        import tempfile
        import os

        content = 'hello world\nfoo bar'
        fd, path = tempfile.mkstemp(suffix='.txt')
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(content)
            result = read_file_content(path)
            self.assertEqual(result, content)
        finally:
            os.unlink(path)
