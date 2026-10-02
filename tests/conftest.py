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
