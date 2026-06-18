# -*- coding: utf-8 -*-

import re
import sys
from string import punctuation
from typing import List, Tuple, Dict

try:
    from validate.utils import (
        error_message,
        check_field_value,
        read_file_lines,
        parse_cli_args,
        exit_on_errors,
        is_category_header,
        is_table_entry,
    )
except ImportError:
    from utils import (
        error_message,
        check_field_value,
        read_file_lines,
        parse_cli_args,
        exit_on_errors,
        is_category_header,
        is_table_entry,
    )

# Temporary replacement
# The descriptions that contain () at the end must adapt to the new policy later
punctuation = punctuation.replace('()', '')

anchor = '###'
auth_keys = ['apiKey', 'OAuth', 'X-Mashape-Key', 'User-Agent', 'No']
https_keys = ['Yes', 'No']
cors_keys = ['Yes', 'No', 'Unknown']

index_title = 0
index_desc = 1
index_auth = 2
index_https = 3
index_cors = 4

num_segments = 5
min_entries_per_category = 3
max_description_length = 100

anchor_re = re.compile(anchor + '\s(.+)')
category_title_in_index_re = re.compile('\*\s\[(.*)\]')
link_re = re.compile('\[(.+)\]\((http.*)\)')

# Type aliases
APIList = List[str]
Categories = Dict[str, APIList]
CategoriesLineNumber = Dict[str, int]


def get_categories_content(contents: List[str]) -> Tuple[Categories, CategoriesLineNumber]:

    categories = {}
    category_line_num = {}

    for line_num, line_content in enumerate(contents):

        if is_category_header(line_content, anchor):
            category = line_content.split(anchor)[1].strip()
            categories[category] = []
            category_line_num[category] = line_num
            continue

        if not is_table_entry(line_content):
            continue

        raw_title = [
            raw_content.strip() for raw_content in line_content.split('|')[1:-1]
        ][0]

        title_match = link_re.match(raw_title)
        if title_match:
                title = title_match.group(1).upper()
                categories[category].append(title)

    return (categories, category_line_num)


def check_alphabetical_order(lines: List[str]) -> List[str]:

    err_msgs = []

    categories, category_line_num = get_categories_content(contents=lines)

    for category, api_list in categories.items():
        if sorted(api_list) != api_list:
            err_msg = error_message(
                category_line_num[category], 
                f'{category} category is not alphabetical order'
            )
            err_msgs.append(err_msg)
    
    return err_msgs


def check_title(line_num: int, raw_title: str) -> List[str]:

    err_msgs = []

    title_match = link_re.match(raw_title)

    # url should be wrapped in "[TITLE](LINK)" Markdown syntax
    if not title_match:
        err_msg = error_message(line_num, 'Title syntax should be "[TITLE](LINK)"')
        err_msgs.append(err_msg)
    else:
        # do not allow "... API" in the entry title
        title = title_match.group(1)
        if title.upper().endswith(' API'):
            err_msg = error_message(line_num, 'Title should not end with "... API". Every entry is an API here!')
            err_msgs.append(err_msg)

    return err_msgs


def check_description(line_num: int, description: str) -> List[str]:

    err_msgs = []

    first_char = description[0]
    if first_char.upper() != first_char:
        err_msg = error_message(line_num, 'first character of description is not capitalized')
        err_msgs.append(err_msg)

    last_char = description[-1]
    if last_char in punctuation:
        err_msg = error_message(line_num, f'description should not end with {last_char}')
        err_msgs.append(err_msg)

    desc_length = len(description)
    if desc_length > max_description_length:
        err_msg = error_message(line_num, f'description should not exceed {max_description_length} characters (currently {desc_length})')
        err_msgs.append(err_msg)
    
    return err_msgs


def check_auth(line_num: int, auth: str) -> List[str]:

    err_msgs = []

    backtick = '`'
    if auth != 'No' and (not auth.startswith(backtick) or not auth.endswith(backtick)):
        err_msg = error_message(line_num, 'auth value is not enclosed with `backticks`')
        err_msgs.append(err_msg)

    if auth.replace(backtick, '') not in auth_keys:
        err_msg = error_message(line_num, f'{auth} is not a valid Auth option')
        err_msgs.append(err_msg)
    
    return err_msgs


def check_https(line_num: int, https: str) -> List[str]:
    return check_field_value(line_num, https, https_keys, 'HTTPS')


def check_cors(line_num: int, cors: str) -> List[str]:
    return check_field_value(line_num, cors, cors_keys, 'CORS')


def check_entry(line_num: int, segments: List[str]) -> List[str]:

    raw_title = segments[index_title]
    description = segments[index_desc]
    auth = segments[index_auth]
    https = segments[index_https]
    cors = segments[index_cors]

    title_err_msgs = check_title(line_num, raw_title)
    desc_err_msgs = check_description(line_num, description)
    auth_err_msgs = check_auth(line_num, auth)
    https_err_msgs = check_https(line_num, https)
    cors_err_msgs = check_cors(line_num, cors)

    err_msgs = [
        *title_err_msgs,
        *desc_err_msgs,
        *auth_err_msgs,
        *https_err_msgs,
        *cors_err_msgs
    ]

    return err_msgs


def check_file_format(lines: List[str]) -> List[str]:

    err_msgs = []
    category_title_in_index = []

    alphabetical_err_msgs = check_alphabetical_order(lines)
    err_msgs.extend(alphabetical_err_msgs)

    num_in_category = min_entries_per_category + 1
    category = ''
    category_line = 0

    for line_num, line_content in enumerate(lines):

        category_title_match = category_title_in_index_re.match(line_content)
        if category_title_match:
            category_title_in_index.append(category_title_match.group(1))

        # check each category for the minimum number of entries
        if is_category_header(line_content, anchor):
            category_match = anchor_re.match(line_content)
            if category_match:
                if category_match.group(1) not in category_title_in_index:
                    err_msg = error_message(line_num, f'category header ({category_match.group(1)}) not added to Index section')
                    err_msgs.append(err_msg)
            else:
                err_msg = error_message(line_num, 'category header is not formatted correctly')
                err_msgs.append(err_msg)

            if num_in_category < min_entries_per_category:
                err_msg = error_message(category_line, f'{category} category does not have the minimum {min_entries_per_category} entries (only has {num_in_category})')
                err_msgs.append(err_msg)

            category = line_content.split(' ')[1]
            category_line = line_num
            num_in_category = 0
            continue

        # skips lines that we do not care about
        if not is_table_entry(line_content):
            continue

        num_in_category += 1
        segments = line_content.split('|')[1:-1]
        if len(segments) < num_segments:
            err_msg = error_message(line_num, f'entry does not have all the required columns (have {len(segments)}, need {num_segments})')
            err_msgs.append(err_msg)
            continue
    
        for segment in segments:
            # every line segment should start and end with exactly 1 space
            if len(segment) - len(segment.lstrip()) != 1 or len(segment) - len(segment.rstrip()) != 1:
                err_msg = error_message(line_num, 'each segment must start and end with exactly 1 space')
                err_msgs.append(err_msg)
        
        segments = [segment.strip() for segment in segments]
        entry_err_msgs = check_entry(line_num, segments)
        err_msgs.extend(entry_err_msgs)
    
    return err_msgs


def main(filename: str) -> None:

    lines = read_file_lines(filename)

    file_format_err_msgs = check_file_format(lines)
    exit_on_errors(file_format_err_msgs)


if __name__ == '__main__':

    args = parse_cli_args(
        min_args=1,
        usage_message='No .md file passed (file should contain Markdown table syntax)'
    )

    filename = args[0]

    main(filename)
