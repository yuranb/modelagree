from pathlib import Path
import re

import pytest

from modelagree import __version__
from modelagree.cli import main


def test_version_matches_package_metadata(capsys):
    metadata = (Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text()
    project = re.search(r'(?ms)^\[project\]\n(.*?)(?=^\[|\Z)', metadata).group(1)
    version = re.search(r'(?m)^version = "([^"]+)"$', project).group(1)
    assert __version__ == version
    with pytest.raises(SystemExit) as result:
        main(['--version'])
    assert result.value.code == 0
    captured = capsys.readouterr()
    assert captured.out == f'modelagree {version}\n'
    assert captured.err == ''
