"""Check documented privacy examples against the shipped Git-ignore rules."""
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest


def test_documented_git_ignore_examples(tmp_path):
    root = Path(__file__).resolve().parents[1]
    readme = (root / 'README.md').read_text(encoding='utf-8')
    section = re.search(r'^## Known limitations\s*\n(.*?)(?=^## |\Z)',
                        readme, re.MULTILINE | re.DOTALL)
    assert section is not None, 'Document the run-artifact trust boundaries'
    examples = re.findall(r'^\|\s*`([^`]+)`\s*\|\s*(yes|no)\s*\|\s*$',
                          section.group(1), re.MULTILINE)
    assert {answer for _, answer in examples} == {'yes', 'no'}, (
        'Document both an ignored output path and an unprotected custom path')
    assert len({path for path, _ in examples}) == len(examples)

    git = shutil.which('git')
    if git is None:
        pytest.skip('Git is needed to verify the documented ignore examples')
    # Isolate the shipped rules from this checkout and user-level exclusions.
    isolated = tmp_path / 'ignore-check'
    isolated.mkdir()
    subprocess.run([git, 'init', '--quiet', '--template=', str(isolated)], check=True,
                   capture_output=True, text=True)
    shutil.copyfile(root / '.gitignore', isolated / '.gitignore')
    result = subprocess.run(
        [git, '-c', f'core.excludesFile={os.devnull}',
         'check-ignore', '--no-index', '--stdin'],
        cwd=isolated, input=''.join(path + '\n' for path, _ in examples),
        capture_output=True, text=True)
    assert result.returncode in (0, 1), result.stderr
    ignored = set(result.stdout.splitlines())
    expected = {path for path, answer in examples if answer == 'yes'}
    assert ignored == expected
