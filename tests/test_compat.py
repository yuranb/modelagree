"""Protect the additive scores contract and frozen 0.1.0 manifest format."""
import json
from pathlib import Path
import shutil

import pytest

from modelagree.cli import main


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / 'tests/golden'


def assert_subset(expected, actual, path=()):
    if isinstance(expected, dict):
        assert isinstance(actual, dict), path
        for key, value in expected.items():
            child = (*path, key)
            if child[-3:] in (
                ('resources', 'latency_seconds', 'total'),
                ('resources', 'attempt_latency_seconds', 'total'),
            ):
                continue
            assert key in actual, child
            assert_subset(value, actual[key], child)
    elif isinstance(expected, list):
        assert isinstance(actual, list), path
        assert len(actual) == len(expected), path
        for index, (value, result) in enumerate(zip(expected, actual)):
            assert_subset(value, result, (*path, index))
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, rel=1e-12), path
    else:
        assert actual == expected, path


@pytest.fixture
def demo_run(tmp_path):
    shutil.copytree(ROOT / 'examples', tmp_path / 'examples')
    assert main(['run', str(tmp_path / 'examples/demo.yaml')]) == 0
    directory = tmp_path / 'runs/demo'
    assert (directory / 'manifest.json').is_file()
    return directory


def test_demo_scores_preserve_v010(demo_run):
    assert main(['score', str(demo_run)]) == 0
    actual = json.loads((demo_run / 'scores.json').read_text())
    expected = json.loads((GOLDEN / 'demo_scores_v0.1.0.json').read_text())
    assert actual['run_fingerprint'] == expected['run_fingerprint']
    assert_subset(expected, actual)


def test_report_accepts_v010_manifest(demo_run):
    manifest = demo_run / 'manifest.json'
    shutil.copyfile(GOLDEN / 'demo_manifest_v0.1.0.json', manifest)
    before = manifest.read_bytes()
    assert main(['report', str(demo_run)]) == 0
    report = (demo_run / 'report.html').read_text()
    assert report.startswith('<!doctype html>')
    assert json.loads(before)['fingerprint'] in report
    assert manifest.read_bytes() == before
