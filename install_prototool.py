# Copyright 2020 The Oppia Authors. All Rights Reserved.
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

"""Installation script for Oppia third-party libraries."""

from __future__ import absolute_import  # pylint: disable=import-only-modules
from __future__ import unicode_literals  # pylint: disable=import-only-modules

import os
import subprocess
import sys
import urllib

THIRD_PARTY_DIR = os.path.join('.', 'third_party')
PROTOTOOL_DIR = os.path.join(THIRD_PARTY_DIR, 'prototool-1.10.0')
PROTOTOOL_URL = (
    'https://github.com/uber/prototool/releases/download/v1.10.0/'
    'prototool-Linux-x86_64')


def download_file(source_url, target_dir, filename):
    """Downloads a file and save it to a given directory.

    File is downloaded only if it does not already exist.

    Args:
        source_url: str. The URL of the file.
        target_dir: str. The directory to save the file to.
        filename: str. Name of the output file.
    """
    os.makedirs(target_dir)
    print('Downloading file %s to %s ...' % (filename, target_dir))
    urllib.urlretrieve(
        source_url, filename=os.path.join(target_dir, filename))
    print('Download of %s succeeded.' % filename)


def make_executable(filepath):
    """Makes the file stored as filepath an executable.

    Args:
        filepath: str. Path to the file.
    """
    if not os.path.exists(filepath):
        print('Unable to make executable. File %s does not exist' % filepath)
        sys.exit(1)
    subprocess.call(['chmod', '+x', filepath])
    print('File %s is now an executable' % filepath)


def main(args=None):
    """Installs all the third party libraries."""
    if not os.path.exists(PROTOTOOL_DIR):
        download_file(PROTOTOOL_URL, PROTOTOOL_DIR, 'prototool')
        make_executable(os.path.join(PROTOTOOL_DIR, 'prototool'))

# The 'no coverage' pragma is used as this line is un-testable. This is because
# it will only be called when install_third_party.py is used as a script.
if __name__ == '__main__': # pragma: no cover
    main()
