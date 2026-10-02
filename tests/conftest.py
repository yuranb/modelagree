import json
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def config_factory(tmp_path):
    def make(items=None, responses=None, models=None, schema=None):
        items = items or [{'id':'one','text':'Invented example.','labels':{'label':'a'}}]
        schema = schema or {'label': {'type':'categorical','labels':['a','b']}}
        responses = responses if responses is not None else {'one':'{"label":"a"}'}
        (tmp_path/'data.jsonl').write_text(''.join(json.dumps(i)+'\n' for i in items))
        (tmp_path/'prompt.txt').write_text('Return labels as JSON.')
        (tmp_path/'responses.json').write_text(json.dumps(responses))
        cfg = {'dataset':'data.jsonl','prompt':'prompt.txt','run_dir':'run',
               'label_schema':schema,'retry_attempts':2,
               'models':models or [{'id':'m','provider':'mock','model':'canned','responses':'responses.json'}]}
        path=tmp_path/'config.yaml'
        path.write_text(yaml.safe_dump(cfg))
        return path
    return make


@pytest.fixture(autouse=True)
def no_real_keys(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)


@pytest.fixture
def tiny_image(tmp_path):
    import base64
    path=tmp_path/'pixel.png'
    path.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWZkAAAAASUVORK5CYII='))
    return path
