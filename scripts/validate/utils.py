# -*- coding: utf-8 -*-

import sys
from typing import List


def error_message(line_number: int, message: str) -> str:
    line = line_number + 1
    return f'(L{line:03d}) {message}'


def check_field_value(line_num: int, value: str, valid_values: List[str], field_name: str) -> List[str]:
    """Validate that a field value is one of the allowed values.

    Used for HTTPS, CORS, and similar column validations where
    the check is simply membership in a fixed set.
    """
    err_msgs = []

    if value not in valid_values:
        err_msg = error_message(line_num, f'{value} is not a valid {field_name} option')
        err_msgs.append(err_msg)

    return err_msgs


def read_file_lines(filename: str) -> List[str]:
    """Read a file and return its lines with trailing whitespace stripped."""
    with open(filename, mode='r', encoding='utf-8') as file:
        return list(line.rstrip() for line in file)


def read_file_content(filename: str) -> str:
    """Read a file and return its full text content."""
    with open(filename, mode='r', encoding='utf-8') as file:
        return file.read()


def parse_cli_args(min_args: int, usage_message: str) -> List[str]:
    """Parse and validate command-line arguments.

    Returns the list of arguments (excluding the script name) if valid.
    Exits with an error message if the minimum argument count is not met.
    """
    args = sys.argv[1:]
    if len(args) < min_args:
        print(usage_message)
        sys.exit(1)
    return args


def exit_on_errors(error_messages: List[str]) -> None:
    """Print error messages and exit with code 1 if any errors exist."""
    if error_messages:
        for msg in error_messages:
            print(msg)
        sys.exit(1)


def is_category_header(line: str, anchor: str) -> bool:
    """Check if a line is a category header (starts with the anchor prefix)."""
    return line.startswith(anchor)


def is_table_entry(line: str) -> bool:
    """Check if a line is a table data entry (starts with | but not a separator)."""
    return line.startswith('|') and not line.startswith('|---')
