# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A module help parse requirements.txt."""
import os
import re
from typing import Set


def parse(path: str) -> Set[str]:
    """Parses requirements given the absolute path of a requirements.txt.

    Note that this function only returns what are the requirements. It will not
    return the version restrictions.

    Args:
        path: Absolute path of a requirements.txt.

    Returns:
        A list of requirements from the requirements.txt.
    """

    results = set()
    if not os.path.exists(path):
        return results

    dir_path = os.path.dirname(path)
    with open(path) as requirements_file:
        lines = requirements_file.read().splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('"""'):
                continue
            elif line.startswith('-r'):
                sub_requirements_path = line.split(' ')[-1]
                results = results.union(
                    parse(os.path.join(dir_path, sub_requirements_path)))
            else:
                results.add(re.split(r'[>=<]', line)[0])
    return results

