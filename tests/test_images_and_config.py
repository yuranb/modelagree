import json

import pytest
import yaml

from modelagree.cli import main
from modelagree.config import load_config
from modelagree.runner import run
from modelagree.storage import read_json, response_path


def test_image_snapshot_and_frozen_content(config_factory,tiny_image):
    cfg=config_factory(items=[{'id':'one','text':'Invented','image':tiny_image.name,'labels':{'label':'a'}}])
    directory=run(cfg)
    rec=read_json(response_path(directory,'m','one'))
    image=rec['request']['image']
    from pathlib import Path
    saved=Path(image['path'])
    assert saved.parent==directory/'images' and saved.read_bytes()==tiny_image.read_bytes()
    tiny_image.write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed'): run(cfg)
    assert saved.read_bytes()!=tiny_image.read_bytes()


def test_image_paths_are_dataset_relative(config_factory,tiny_image):
    cfg=config_factory(items=[{'id':'one','text':'Invented','image':tiny_image.name,'labels':{}}])
    nested=cfg.parent/'nested'; nested.mkdir()
    (cfg.parent/'data.jsonl').rename(nested/'data.jsonl')
    tiny_image.rename(nested/tiny_image.name)
    data=yaml.safe_load(cfg.read_text()); data['dataset']='nested/data.jsonl'; cfg.write_text(yaml.safe_dump(data))
    frozen,_=load_config(cfg)
    assert frozen['items'][0]['image']['path']==str(nested/tiny_image.name)


def test_limit_freezes_first_items_and_requires_same_limit_on_resume(config_factory):
    cfg=config_factory(items=[{'id':str(i),'text':'Invented','labels':{'label':'a'}} for i in range(3)],
                       responses={str(i):'{"label":"a"}' for i in range(3)})
    directory=run(cfg,limit=2)
    assert [i['id'] for i in read_json(directory/'manifest.json')['items']]==['0','1']
    assert len(list((directory/'responses').rglob('*.json')))==2
    run(cfg,limit=2)
    with pytest.raises(ValueError,match='changed'): run(cfg)
    assert main(['run',str(cfg),'--limit','2'])==0
    assert main(['run',str(cfg),'--limit','0'])==1


@pytest.mark.parametrize('provider,parameters', [('openai',{'api_key':'forbidden'}),
    ('openai',{'instructions':'prompt override'}),('openai',{'temperature':float('nan')}),
    ('openai',{'max_output_tokens':True}),('openai',{'reasoning_effort':'invalid'}),
    ('gemini',{'seed':-1}),('gemini',{'top_p':2}),('gemini',{'top_k':0})])
def test_invalid_parameters_rejected(config_factory,provider,parameters):
    cfg=config_factory(models=[{'id':'m','provider':provider,'model':'test-model','parameters':parameters}])
    with pytest.raises(ValueError): load_config(cfg)
    assert not (cfg.parent/'run').exists()


def test_keys_rejected_in_config_and_scrubbed_from_cli(config_factory,monkeypatch,capsys):
    monkeypatch.setenv('OPENAI_API_KEY','dummy-secret-key')
    cfg=config_factory()
    (cfg.parent/'prompt.txt').write_text('accidental dummy-secret-key')
    assert main(['run',str(cfg)])==1
    assert 'dummy-secret-key' not in capsys.readouterr().err
    assert not (cfg.parent/'run').exists()
    (cfg.parent/'prompt.txt').write_text('safe')
    data=yaml.safe_load(cfg.read_text()); data['api_key']='dummy-secret-key'; cfg.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError,match='environment'): load_config(cfg)


@pytest.mark.parametrize('kind', ['categorical', 'ordinal', 'multi_label'])
@pytest.mark.parametrize('extra', ['api_key', 'lables', 'wrong_vocabulary'])
def test_unknown_schema_options_rejected_before_persistence(config_factory, kind, extra):
    vocabulary = 'levels' if kind == 'ordinal' else 'labels'
    unknown = ('labels' if kind == 'ordinal' else 'levels') if extra == 'wrong_vocabulary' else extra
    spec = {'type': kind, vocabulary: ['a', 'b'], unknown: 'dummy-schema-credential'}
    cfg = config_factory(schema={'label': spec})
    with pytest.raises(ValueError, match='Unsupported schema keys') as exc:
        run(cfg)
    assert 'dummy-schema-credential' not in str(exc.value)
    assert not (cfg.parent / 'run').exists()


def test_placeholder_prevents_http(config_factory):
    cfg=config_factory(models=[{'id':'m','provider':'gemini','model':'REPLACE_WITH_GEMINI_MODEL_ID'}])
    with pytest.raises(ValueError,match='placeholder'): run(cfg)


def test_limit_does_not_load_unselected_images(config_factory):
    cfg=config_factory(items=[{'id':'one','text':'Invented','labels':{'label':'a'}},
                              {'id':'two','text':'Invented','image':'missing.png','labels':{}}])
    assert run(cfg,limit=1).is_dir()


def test_modified_image_snapshot_cannot_be_sent(config_factory,tiny_image,monkeypatch):
    from pathlib import Path
    from modelagree import runner
    from modelagree.providers.base import ProviderError, Response
    class Down:
        def generate(self,request): raise ProviderError('timeout',True)
    monkeypatch.setattr(runner,'create_provider',lambda m:Down())
    monkeypatch.setattr(runner.time,'sleep',lambda n:None)
    cfg=config_factory(items=[{'id':'one','text':'Invented','image':tiny_image.name,'labels':{'label':'a'}}])
    directory=run(cfg)
    saved=Path(read_json(response_path(directory,'m','one'))['request']['image']['path'])
    saved.write_bytes(b'corrupted snapshot')
    class Never:
        def generate(self,request): raise AssertionError('corrupted image sent')
    monkeypatch.setattr(runner,'create_provider',lambda m:Never())
    with pytest.raises(ValueError,match='changed'): run(cfg)
