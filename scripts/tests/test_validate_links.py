# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import requests

from validate.links import find_links_in_text
from validate.links import find_links_in_file
from validate.links import check_duplicate_links
from validate.links import fake_user_agent
from validate.links import get_host_from_link
from validate.links import has_cloudflare_protection
from validate.links import check_if_link_is_working
from validate.links import check_if_list_of_links_are_working
from validate.links import start_duplicate_links_checker
from validate.links import start_links_working_checker
from validate.links import main as links_main


class FakeResponse():
    def __init__(self, code: int, headers: dict, text: str) -> None:
        self.status_code = code
        self.headers = headers
        self.text = text


class TestValidateLinks(unittest.TestCase):

    def setUp(self):
        self.duplicate_links = [
            'https://www.example.com',
            'https://www.example.com',
            'https://www.example.com',
            'https://www.anotherexample.com',
        ]
        self.no_duplicate_links = [
            'https://www.firstexample.com',
            'https://www.secondexample.com',
            'https://www.anotherexample.com',
        ]

        self.code_200 = 200
        self.code_403 = 403
        self.code_503 = 503

        self.cloudflare_headers = {'Server': 'cloudflare'}
        self.no_cloudflare_headers = {'Server': 'google'}

        self.text_with_cloudflare_flags = '403 Forbidden Cloudflare We are checking your browser...'
        self.text_without_cloudflare_flags = 'Lorem Ipsum'

    def test_find_link_in_text(self):
        text = """
            # this is valid

            http://example.com?param1=1&param2=2#anchor
            https://www.example.com?param1=1&param2=2#anchor
            https://www.example.com.br
            https://www.example.com.gov.br
            [Example](https://www.example.com?param1=1&param2=2#anchor)
            lorem ipsum https://www.example.com?param1=1&param2=2#anchor
            https://www.example.com?param1=1&param2=2#anchor lorem ipsum

            # this not is valid

            example.com
            https:example.com
            https:/example.com
            https//example.com
            https//.com
        """

        links = find_links_in_text(text)

        self.assertIsInstance(links, list)
        self.assertEqual(len(links), 7)

        for link in links:
            with self.subTest():
                self.assertIsInstance(link, str)

    def test_find_link_in_text_with_invalid_argument(self):
        with self.assertRaises(TypeError):
            find_links_in_text()
            find_links_in_text(1)
            find_links_in_text(True)

    def test_if_check_duplicate_links_has_the_correct_return(self):
        result_1 = check_duplicate_links(self.duplicate_links)
        result_2 = check_duplicate_links(self.no_duplicate_links)

        self.assertIsInstance(result_1, tuple)
        self.assertIsInstance(result_2, tuple)

        has_duplicate_links, links = result_1
        no_duplicate_links, no_links = result_2

        self.assertTrue(has_duplicate_links)
        self.assertFalse(no_duplicate_links)

        self.assertIsInstance(links, list)
        self.assertIsInstance(no_links, list)

        self.assertEqual(len(links), 2)
        self.assertEqual(len(no_links), 0)

    def test_if_fake_user_agent_has_a_str_as_return(self):
        user_agent = fake_user_agent()
        self.assertIsInstance(user_agent, str)

    def test_get_host_from_link(self):
        links = [
            'example.com',
            'https://example.com',
            'https://www.example.com',
            'https://www.example.com.br',
            'https://www.example.com/route',
            'https://www.example.com?p=1&q=2',
            'https://www.example.com#anchor'
        ]

        for link in links:
            host = get_host_from_link(link)

            with self.subTest():
                self.assertIsInstance(host, str)

                self.assertNotIn('://', host)
                self.assertNotIn('/', host)
                self.assertNotIn('?', host)
                self.assertNotIn('#', host)

        with self.assertRaises(TypeError):
            get_host_from_link()

    def test_has_cloudflare_protection_with_code_403_and_503_in_response(self):
        resp_with_cloudflare_protection_code_403 = FakeResponse(
            code=self.code_403,
            headers=self.cloudflare_headers,
            text=self.text_with_cloudflare_flags
        )

        resp_with_cloudflare_protection_code_503 = FakeResponse(
            code=self.code_503,
            headers=self.cloudflare_headers,
            text=self.text_with_cloudflare_flags
        )

        result1 = has_cloudflare_protection(resp_with_cloudflare_protection_code_403)
        result2 = has_cloudflare_protection(resp_with_cloudflare_protection_code_503)

        self.assertTrue(result1)
        self.assertTrue(result2)

    def test_has_cloudflare_protection_when_there_is_no_protection(self):
        resp_without_cloudflare_protection1 = FakeResponse(
            code=self.code_200,
            headers=self.no_cloudflare_headers,
            text=self.text_without_cloudflare_flags
        )

        resp_without_cloudflare_protection2 = FakeResponse(
            code=self.code_403,
            headers=self.no_cloudflare_headers,
            text=self.text_without_cloudflare_flags
        )

        resp_without_cloudflare_protection3 = FakeResponse(
            code=self.code_503,
            headers=self.no_cloudflare_headers,
            text=self.text_without_cloudflare_flags
        )

        result1 = has_cloudflare_protection(resp_without_cloudflare_protection1)
        result2 = has_cloudflare_protection(resp_without_cloudflare_protection2)
        result3 = has_cloudflare_protection(resp_without_cloudflare_protection3)

        self.assertFalse(result1)
        self.assertFalse(result2)
        self.assertFalse(result3)

    def test_has_cloudflare_protection_with_cloudflare_server_but_no_flags(self):
        resp = FakeResponse(
            code=403,
            headers={'Server': 'cloudflare'},
            text='Some other error page without flags'
        )
        self.assertFalse(has_cloudflare_protection(resp))

    def test_find_links_in_file(self):
        content = (
            '## Index\n'
            '| [Example](https://www.example.com) | Desc | No | Yes | Yes |\n'
            '| [Another](https://www.another.com/path) | Desc | No | Yes | Yes |\n'
        )
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            tmpfile = f.name
        try:
            links = find_links_in_file(tmpfile)
            self.assertIsInstance(links, list)
            self.assertEqual(len(links), 2)
            self.assertIn('https://www.example.com', links)
            self.assertIn('https://www.another.com/path', links)
        finally:
            os.unlink(tmpfile)

    def test_find_links_in_file_without_index_section(self):
        content = (
            'Some header\n'
            'https://www.example.com\n'
        )
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            tmpfile = f.name
        try:
            links = find_links_in_file(tmpfile)
            self.assertIsInstance(links, list)
            self.assertGreater(len(links), 0)
        finally:
            os.unlink(tmpfile)

    @patch('validate.links.requests.get')
    def test_check_if_link_is_working_with_status_200(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {'Server': 'nginx'}
        mock_resp.text = 'OK'
        mock_get.return_value = mock_resp

        has_error, error_message = check_if_link_is_working('https://www.example.com')
        self.assertFalse(has_error)
        self.assertEqual(error_message, '')

    @patch('validate.links.requests.get')
    def test_check_if_link_is_working_with_status_404(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.headers = {'Server': 'nginx'}
        mock_resp.text = 'Not Found'
        mock_get.return_value = mock_resp

        has_error, error_message = check_if_link_is_working('https://www.example.com')
        self.assertTrue(has_error)
        self.assertIn('ERR:CLT', error_message)
        self.assertIn('404', error_message)

    @patch('validate.links.requests.get')
    def test_check_if_link_is_working_with_cloudflare_protection(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.headers = {'Server': 'cloudflare'}
        mock_resp.text = '403 Forbidden Cloudflare We are checking your browser...'
        mock_resp.__class__ = requests.models.Response
        mock_get.return_value = mock_resp

        has_error, error_message = check_if_link_is_working('https://www.example.com')
        self.assertFalse(has_error)
        self.assertEqual(error_message, '')

    @patch('validate.links.requests.get')
    def test_check_if_link_is_working_with_ssl_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.SSLError('SSL certificate verify failed')

        has_error, error_message = check_if_link_is_working('https://www.example.com')
        self.assertTrue(has_error)
        self.assertIn('ERR:SSL', error_message)

    @patch('validate.links.requests.get')
    def test_check_if_link_is_working_with_connection_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError('Connection refused')

        has_error, error_message = check_if_link_is_working('https://www.example.com')
        self.assertTrue(has_error)
        self.assertIn('ERR:CNT', error_message)

    @patch('validate.links.requests.get')
    def test_check_if_link_is_working_with_timeout(self, mock_get):
        mock_get.side_effect = TimeoutError('Connection timed out')

        has_error, error_message = check_if_link_is_working('https://www.example.com')
        self.assertTrue(has_error)
        self.assertIn('ERR:TMO', error_message)

    @patch('validate.links.requests.get')
    def test_check_if_link_is_working_with_too_many_redirects(self, mock_get):
        mock_get.side_effect = requests.exceptions.TooManyRedirects('Exceeded max redirects')

        has_error, error_message = check_if_link_is_working('https://www.example.com')
        self.assertTrue(has_error)
        self.assertIn('ERR:TMR', error_message)

    @patch('validate.links.requests.get')
    def test_check_if_link_is_working_with_unknown_error(self, mock_get):
        mock_get.side_effect = Exception('Unknown error')

        has_error, error_message = check_if_link_is_working('https://www.example.com')
        self.assertTrue(has_error)
        self.assertIn('ERR:UKN', error_message)

    @patch('validate.links.check_if_link_is_working')
    def test_check_if_list_of_links_are_working_all_ok(self, mock_check):
        mock_check.return_value = (False, '')

        errors = check_if_list_of_links_are_working(['https://a.com', 'https://b.com'])
        self.assertIsInstance(errors, list)
        self.assertEqual(len(errors), 0)

    @patch('validate.links.check_if_link_is_working')
    def test_check_if_list_of_links_are_working_with_errors(self, mock_check):
        mock_check.side_effect = [
            (True, 'ERR:CLT: 404 : https://a.com'),
            (False, ''),
            (True, 'ERR:TMO: https://c.com'),
        ]

        errors = check_if_list_of_links_are_working([
            'https://a.com', 'https://b.com', 'https://c.com'
        ])
        self.assertIsInstance(errors, list)
        self.assertEqual(len(errors), 2)
        self.assertIn('ERR:CLT', errors[0])
        self.assertIn('ERR:TMO', errors[1])

    @patch('builtins.print')
    def test_start_duplicate_links_checker_no_duplicates(self, mock_print):
        links = ['https://a.com', 'https://b.com']
        start_duplicate_links_checker(links)
        mock_print.assert_any_call('No duplicate links.')

    @patch('builtins.print')
    def test_start_duplicate_links_checker_with_duplicates(self, mock_print):
        links = ['https://a.com', 'https://a.com', 'https://b.com']
        with self.assertRaises(SystemExit) as ctx:
            start_duplicate_links_checker(links)
        self.assertEqual(ctx.exception.code, 1)

    @patch('validate.links.check_if_list_of_links_are_working')
    @patch('builtins.print')
    def test_start_links_working_checker_all_ok(self, mock_print, mock_check):
        mock_check.return_value = []
        start_links_working_checker(['https://a.com'])
        mock_print.assert_any_call('Checking if 1 links are working...')

    @patch('validate.links.check_if_list_of_links_are_working')
    @patch('builtins.print')
    def test_start_links_working_checker_with_errors(self, mock_print, mock_check):
        mock_check.return_value = ['ERR:CLT: 404 : https://a.com']
        with self.assertRaises(SystemExit) as ctx:
            start_links_working_checker(['https://a.com'])
        self.assertEqual(ctx.exception.code, 1)

    @patch('validate.links.start_links_working_checker')
    @patch('validate.links.start_duplicate_links_checker')
    @patch('validate.links.find_links_in_file')
    def test_main_with_only_duplicate_checker(self, mock_find, mock_dup, mock_work):
        mock_find.return_value = ['https://a.com']
        links_main('fake.md', only_duplicate_links_checker=True)
        mock_find.assert_called_once_with('fake.md')
        mock_dup.assert_called_once()
        mock_work.assert_not_called()

    @patch('validate.links.start_links_working_checker')
    @patch('validate.links.start_duplicate_links_checker')
    @patch('validate.links.find_links_in_file')
    def test_main_with_full_check(self, mock_find, mock_dup, mock_work):
        mock_find.return_value = ['https://a.com']
        links_main('fake.md', only_duplicate_links_checker=False)
        mock_find.assert_called_once_with('fake.md')
        mock_dup.assert_called_once()
        mock_work.assert_called_once()
