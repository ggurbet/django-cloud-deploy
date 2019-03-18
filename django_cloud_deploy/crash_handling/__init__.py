# Copyright 2018 Google LLC
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
"""A module handles crashes of the tool."""

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import traceback
import urllib.parse

import jinja2

from django_cloud_deploy import __version__
from django_cloud_deploy.cli import io
from django_cloud_deploy.utils import webbrowser


class UserError(Exception):
    """Error caused by user's code."""


# A list of exceptions that should be displayed to the user rather than opening
# a Github issue.
_DISPLAYABLE_EXCEPTIONS = [UserError]


# The Github issue label for all issues generated by crash handling
_ISSUE_LABEL = 'crash handler'


with open(os.path.join(os.path.dirname(__file__), 'template',
                       'issue_template.txt')) as f:
    _ISSUE_TEMPLATE = f.read()


def handle_crash(err: Exception, command: str, console: io.IO = io.ConsoleIO()):
    """The tool's crashing handler.

    Args:
        err: The exception that was raised.
        command: The command causing the exception to get thrown,
            e.g. 'django-cloud-deploy new'.
        console: Object to use for user I/O.
    """

    # Only handle crashes caused by our code, not user's code.
    # When deploying, our tool will run the code of user's Django project.
    # If user's code has a bug, then an UserError will be raised. In this case,
    # we do not want users to create a Github issue.
    if any(
            isinstance(err, exception_class)
            for exception_class in _DISPLAYABLE_EXCEPTIONS):
        # https://github.com/google/pytype/issues/225
        raise err.__cause__  # pytype: disable=attribute-error

    log_fd, log_file_path = tempfile.mkstemp(
        prefix='django-deploy-bug-report-')
    issue_content = _create_issue_body(command)
    issue_title = _create_issue_title(err, command)
    log_file = os.fdopen(log_fd, 'wt')
    log_file.write(issue_content)
    log_file.close()

    console.tell(
        ('Your "{}" failed due to an internal error.'
         '\n\n'
         'You can report this error by filing a bug on Github. If you agree,\n'
         'a browser window will open and an Github issue will be\n'
         'pre-populated with the details of this crash.\n'
         'For more details, see: {}').format(command, log_file_path))

    while True:
        ans = console.ask('Would you like to file a bug? [y/N]: ')
        ans = ans.strip().lower()
        if not ans:  # 'N' is default.
            break

        if ans in ['y', 'n']:
            break

    if ans.lower() == 'y':
        _create_issue(issue_title, issue_content)


def _create_issue(issue_title: str, issue_content: str):
    """Open browser to create a issue on the package's Github repo.

    Args:
        issue_title: Title of the Github issue.
        issue_content: Body of the Github issue.
    """

    request_url = ('https://github.com/GoogleCloudPlatform/django-cloud-deploy/'
                   'issues/new?{}')

    params = urllib.parse.urlencode(
        {'title': issue_title, 'body': issue_content, 'labels': _ISSUE_LABEL})
    url = request_url.format(params)
    webbrowser.open_url(url)


def _create_issue_title(err: Exception, command: str) -> str:
    """Generate a Github issue title based on given exception and command."""
    return '{}:{} during "{}"'.format(type(err).__name__, str(err), command)


def _create_issue_body(command: str) -> str:
    """Generate a Github issue body based on given exception and command.

    Args:
        command: The command causing the exception to get thrown,
            e.g. 'django-cloud-deploy new'.

    Returns:
        Github issue body in string.
    """
    template_env = jinja2.Environment()

    gcloud_path = shutil.which('gcloud')
    if gcloud_path:
        try:
            gcloud_version = subprocess.check_output(
                [gcloud_path, 'info', '--format=value(basic.version)'],
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True).rstrip()
        except subprocess.CalledProcessError as e:
            gcloud_version = 'Error: {!r}'.format(e.stderr)
    else:
        gcloud_version = 'Not installed or not on PATH'

    docker_path = shutil.which('docker')
    if docker_path:
        try:
            docker_version = subprocess.check_output(
                ['docker', '--version'],
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True).rstrip()
        except subprocess.CalledProcessError:
            docker_version = 'Error: {!r}'.format(e.stderr)
    else:
        docker_version = 'Not installed or not on PATH'

    cloud_sql_proxy_path = shutil.which('cloud_sql_proxy')
    if cloud_sql_proxy_path:
        try:
            cloud_sql_proxy_version = subprocess.check_output(
                [cloud_sql_proxy_path, '--version'],
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True).rstrip()
        except subprocess.CalledProcessError:
            cloud_sql_proxy_version = 'Error: {!r}'.format(e.stderr)
    else:
        cloud_sql_proxy_version = 'Not installed or not on PATH'

    template = template_env.from_string(_ISSUE_TEMPLATE)
    options = {
        'django_cloud_deploy_version': __version__.__version__,
        'command': command,
        'gcloud_version': gcloud_version,
        'docker_version': docker_version,
        'cloud_sql_proxy_version': cloud_sql_proxy_version,
        'python_version': sys.version.replace('\n', ' '),
        'traceback': traceback.format_exc(),
        'platform': platform.platform(),
    }
    content = template.render(options)
    return content
