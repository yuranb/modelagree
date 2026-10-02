import json
import socket
import warnings

import pytest
import yaml
from pytest_socket import SocketBlockedError

from modelagree import runner
from modelagree.providers.base import ProviderError, Response
from modelagree.scoring import score
from modelagree.storage import read_json, response_path, run_lock


@pytest.mark.parametrize('raw', ['{"label":1e999}', '{"label":"\\ud800"}',
                                 '{"label":"\ud800"}'], ids=['overflow', 'escaped-surrogate', 'surrogate'])
def test_unserializable_labels_preserve_completion(config_factory, monkeypatch, raw):
    calls = []
    class Provider:
        def generate(self, request):
            calls.append(request)
            return Response(raw)
    monkeypatch.setattr(runner, 'create_provider', lambda model: Provider())
    config = config_factory()
    directory = runner.run(config)
    path = response_path(directory, 'm', 'one')
    before = path.read_bytes()
    record = read_json(path)
    assert record['status'] == 'completed'
    assert record['raw_response'] == raw
    counts = score(directory)['models']['m']['fields']['label']['counts']
    assert counts['invalid_prediction'] == 1 and counts['eligible'] == 0
    runner.run(config)
    assert len(calls) == 1
    assert path.read_bytes() == before


def test_completion_is_saved_without_label_parsing(config_factory, monkeypatch):
    def broken_parser(*args):
        raise AssertionError('label parsing ran before persistence')
    monkeypatch.setattr(runner, 'parse_response', broken_parser, raising=False)
    directory = runner.run(config_factory())
    record = read_json(response_path(directory, 'm', 'one'))
    assert record['status'] == 'completed' and record['raw_response'] == '{"label":"a"}'
    assert record['parsed'] is None


def test_network_disabled():
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with pytest.raises(SocketBlockedError): socket.socket()


def test_resume_preserves_even_invalid_completion(config_factory, monkeypatch):
    config=config_factory(responses={'one':'not JSON'})
    directory=runner.run(config)
    path=response_path(directory,'m','one')
    before=path.read_bytes()
    assert read_json(path)['status']=='completed'
    class Never:
        def generate(self, request): raise AssertionError('re-requested completion')
    monkeypatch.setattr(runner,'create_provider',lambda m:Never())
    runner.run(config)
    assert path.read_bytes()==before
    assert read_json(path)['parsed'] is None
    assert score(directory)['models']['m']['fields']['label']['counts']['invalid_prediction'] == 1


@pytest.mark.parametrize('retryable,expected',[(True,2),(False,1)])
def test_only_infrastructure_failures_retry(config_factory, monkeypatch, retryable, expected):
    calls=[]
    class Flaky:
        def generate(self, request):
            calls.append(request)
            if len(calls)==1: raise ProviderError('timeout' if retryable else 'auth',retryable)
            return Response('{"label":"a"}',input_tokens=2,output_tokens=3,total_tokens=5)
    monkeypatch.setattr(runner,'create_provider',lambda m:Flaky())
    monkeypatch.setattr(runner.time,'sleep',lambda n:None)
    config=config_factory(); directory=runner.run(config)
    record=read_json(response_path(directory,'m','one'))
    assert len(calls)==expected
    assert len(record['attempts'])==expected
    assert 'labels' not in calls[0]  # Never leak the ground truth to the model.
    if retryable:
        assert record['usage']['total_tokens']==5 and record['status']=='completed'
        assert record['latency_seconds']>=0 and record['started_at']<=record['finished_at']
    else:
        assert record['status']=='permanent_error'
    runner.run(config); assert len(calls)==expected


def test_exhausted_infrastructure_failure_can_resume(config_factory, monkeypatch):
    class Down:
        def generate(self, request): raise ProviderError('http_503',True)
    monkeypatch.setattr(runner,'create_provider',lambda m:Down())
    monkeypatch.setattr(runner.time,'sleep',lambda n:None)
    config=config_factory(); directory=runner.run(config)
    assert read_json(response_path(directory,'m','one'))['status']=='retryable_error'
    class Up:
        def generate(self,request): return Response('{"label":"b"}')
    monkeypatch.setattr(runner,'create_provider',lambda m:Up())
    runner.run(config)
    record=read_json(response_path(directory,'m','one'))
    assert record['status']=='completed' and len(record['attempts'])==3


@pytest.mark.parametrize('filename',['prompt.txt','data.jsonl','responses.json'])
def test_frozen_inputs_reject_changes(config_factory,filename):
    cfg=config_factory(); directory=runner.run(cfg)
    path=cfg.parent/filename
    if filename=='prompt.txt': path.write_text('Changed prompt')
    elif filename=='data.jsonl': path.write_text(json.dumps({'id':'one','text':'changed','labels':{'label':'a'}}))
    else: path.write_text('{"one":"changed"}')
    with pytest.raises(ValueError,match='changed'): runner.run(cfg)
    assert read_json(response_path(directory,'m','one'))['raw_response']=='{"label":"a"}'


def test_lock_prevents_concurrent_runs(tmp_path):
    with run_lock(tmp_path):
        with pytest.raises(ValueError,match='locked'):
            with run_lock(tmp_path): pass
    assert not (tmp_path/'.run.lock').exists()


def test_duplicate_model_and_item_ids_rejected(config_factory):
    model={'id':'m','provider':'mock','model':'canned','responses':'responses.json'}
    cfg=config_factory(models=[model,model])
    with pytest.raises(ValueError,match='unique'): runner.run(cfg)
    item={'id':'one','text':'text','labels':{}}
    cfg=config_factory(items=[item,item])
    with pytest.raises(ValueError,match='Duplicate'): runner.run(cfg)
