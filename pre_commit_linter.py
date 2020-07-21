# coding: utf-8
#
# Copyright 2017 The Oppia Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Pre-commit script for oppia-ml-proto.

This script lints Python code, and prints a
list of lint errors to the terminal. If the directory path is passed,
it will lint all Python files in that directory; otherwise,
it will only lint files that have been touched in this commit.

IMPORTANT NOTES:

1.  Before running this script, you must install third-party dependencies by
    running

        python install_prototool.py

    at least once.

=====================
CUSTOMIZATION OPTIONS
=====================
1.  To lint only files that have been touched in this commit
        python pre_commit_linter.py

2.  To lint all files in the folder or to lint just a specific file
        python pre_commit_linter.py --path filepath

3.  To lint a specific list of files (*.py only). Separate files by spaces
        python pre_commit_linter.py --files file_1 file_2 ... file_n

Note that the root folder MUST be named 'oppia-ml-proto'.
"""

# Pylint has issues with the import order of argparse.
# pylint: disable=wrong-import-order
import argparse
import fnmatch
import multiprocessing
import os
import subprocess
import sys
import time
# pylint: enable=wrong-import-order

_PARSER = argparse.ArgumentParser()
_EXCLUSIVE_GROUP = _PARSER.add_mutually_exclusive_group()
_EXCLUSIVE_GROUP.add_argument(
    '--path',
    help='path to the directory with files to be linted',
    action='store')
_EXCLUSIVE_GROUP.add_argument(
    '--files',
    nargs='+',
    help='specific files to be linted. Space separated list',
    action='store')

if not os.getcwd().endswith('oppia-ml-proto'):
    print('')
    print('ERROR    Please run this script from the oppia root directory.')

_PROTOTOOL_PATH = os.path.join(
    os.getcwd(), 'third_party', 'prototool-1.10.0', 'prototool')

if not os.path.exists(_PROTOTOOL_PATH):
    print('')
    print('ERROR    Please run install_prototool.py first to install prototool')
    sys.exit(1)

_MESSAGE_TYPE_SUCCESS = 'SUCCESS'
_MESSAGE_TYPE_FAILED = 'FAILED'

EXCLUDED_PATHS = ('third_party/*', '.git/*', '.github/*')

PROTOTOOL_CONFIG_FILE = 'prototool_config.json'

def _get_changed_filenames():
    """Returns a list of modified files (both staged and unstaged).

    Returns:
        list(str). A list of filenames of modified files.
    """
    unstaged_files = subprocess.check_output([
        'git', 'diff', '--name-only',
        '--diff-filter=ACM']).splitlines()
    staged_files = subprocess.check_output([
        'git', 'diff', '--cached', '--name-only',
        '--diff-filter=ACM']).splitlines()
    return unstaged_files + staged_files


def _get_all_files_in_directory(dir_path):
    """Recursively collects all files in directory and
    subdirectories of specified path.

    Args:
        dir_path: str. Path to the folder to be linted.

    Returns:
        list(str). A list of files in directory and subdirectories without
        excluded files.
    """
    files_in_directory = []
    for _dir, _, files in os.walk(dir_path):
        for file_name in files:
            filename = os.path.relpath(
                os.path.join(_dir, file_name), os.getcwd())

            files_in_directory.append(filename)
    return files_in_directory


def _lint_proto_files(files_to_lint, result, config):
    """Prints a list of lint errors in the given list of Proto files.

    Args:
        files_to_lint: list(str). A list of filepaths to lint.
        result: multiprocessing.Queue. A queue to put results of test.
    """
    errors_exist = False

    num_proto_files = len(files_to_lint)
    if not files_to_lint:
        result.put('')
        print('There are no Proto files to lint.')
        return

    print('Linting %s Proto files' % num_proto_files)

    _BATCH_SIZE = 50
    current_batch_start_index = 0

    start_time = time.time()

    for proto_file in files_to_lint:
        print('Linting %s' % proto_file)
        try:
            subprocess.check_output([
                _PROTOTOOL_PATH, 'lint', proto_file, '--config-data', config])
        except subprocess.CalledProcessError as e:
            print(e.output)
            errors_exist = True

    if errors_exist:
        result.put('%s    Proto linting failed' % _MESSAGE_TYPE_FAILED)
    else:
        result.put('%s   %s Proto files linted (%.1f secs)' % (
            _MESSAGE_TYPE_SUCCESS, num_proto_files, time.time() - start_time))

    print('Proto linting finished.')

def _get_all_files():
    """This function is used to check if this script is run from
    root directory and to return a list of all the files for linting and
    pattern checks.
    """
    parsed_args = _PARSER.parse_args()
    if parsed_args.path:
        input_path = os.path.join(os.getcwd(), parsed_args.path)
        if not os.path.exists(input_path):
            print('Could not locate file or directory %s. Exiting.' % input_path)
            print('----------------------------------------')
            sys.exit(1)
        if os.path.isfile(input_path):
            all_files = [input_path]
        else:
            all_files = _get_all_files_in_directory(
                input_path)
    elif parsed_args.files:
        valid_filepaths = []
        invalid_filepaths = []
        for f in parsed_args.files:
            if os.path.isfile(f):
                valid_filepaths.append(f)
            else:
                invalid_filepaths.append(f)
        if invalid_filepaths:
            print(
                'The following file(s) do not exist: %s\n'
                'Exiting.' % invalid_filepaths)
            sys.exit(1)
        all_files = valid_filepaths
    else:
        all_files = _get_changed_filenames()
    all_files = [
        filename for filename in all_files if not
        any(fnmatch.fnmatch(filename, pattern) for pattern in EXCLUDED_PATHS)]
    return all_files


def _pre_commit_linter(all_files):
    print('Starting linter...')

    if not os.path.isfile(PROTOTOOL_CONFIG_FILE):
        print('Could not locate config file. Exiting.' % PROTOTOOL_CONFIG_FILE)
        print('----------------------------------------')
        sys.exit(1)

    f = open(PROTOTOOL_CONFIG_FILE, 'r')
    prototool_config = f.read()
    f.close()

    proto_files_to_lint = [
        filename for filename in all_files if filename.endswith('.proto')]

    proto_linting_processes = []

    proto_result = multiprocessing.Queue()
    proto_linting_processes.append(multiprocessing.Process(
        target=_lint_proto_files,
        args=(proto_files_to_lint, proto_result, prototool_config)))

    print('Starting Proto Linting')
    print('----------------------------------------')

    for process in proto_linting_processes:
        process.start()

    for process in proto_linting_processes:
        # Require timeout parameter to prevent against endless waiting for the
        # linting function to return.
        process.join(timeout=600)

    print('')
    print('----------------------------------------')
    summary_messages = []

    # Require block = False to prevent unnecessary waiting for the process
    # output.
    summary_messages.append(proto_result.get(block=False))
    print('\n'.join(summary_messages))
    print('')
    return summary_messages


def _check_newline_character(all_files):
    """This function is used to check that each file
    ends with a single newline character.
    """
    print('Starting newline-at-EOF checks')
    print('----------------------------------------')
    total_files_checked = 0
    total_error_count = 0
    summary_messages = []
    all_files = [
        filename for filename in all_files if not
        any(fnmatch.fnmatch(filename, pattern) for pattern in EXCLUDED_PATHS)]
    failed = False
    for filename in all_files:
        with open(filename, 'rb') as f:
            total_files_checked += 1
            total_num_chars = 0
            for line in f:
                total_num_chars += len(line)
            if total_num_chars == 1:
                failed = True
                print('%s --> Error: Only one character in file' % filename)
                total_error_count += 1
            elif total_num_chars > 1:
                f.seek(-2, 2)
                if not (f.read(1) != '\n' and f.read(1) == '\n'):
                    failed = True
                    print(
                        '%s --> Please ensure that this file ends'
                        'with exactly one newline char.' % filename)
                    total_error_count += 1

    if failed:
        summary_message = '%s   Newline character checks failed' % (
            _MESSAGE_TYPE_FAILED)
        summary_messages.append(summary_message)
    else:
        summary_message = '%s   Newline character checks passed' % (
            _MESSAGE_TYPE_SUCCESS)
        summary_messages.append(summary_message)

    print('')
    print('----------------------------------------')
    print('')
    if total_files_checked == 0:
        print('There are no files to be checked.')
    else:
        print('%s files checked, %s errors found' % (
            total_files_checked, total_error_count))
        print(summary_message)

    return summary_messages


def main():
    all_files = _get_all_files()
    newline_messages = _check_newline_character(all_files)
    linter_messages = _pre_commit_linter(all_files)
    all_messages = linter_messages + newline_messages
    if any([message.startswith(_MESSAGE_TYPE_FAILED) for message in
            all_messages]):
        sys.exit(1)


if __name__ == '__main__':
    main()
