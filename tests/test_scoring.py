import json
from pathlib import Path

from modelagree.cli import main
from modelagree.report import report
from modelagree.runner import run
from modelagree.scoring import score
from modelagree.storage import read_json, write_json, response_path


def test_unknown_invalid_overlap_pairwise_and_model_ids(config_factory):
    items=[{'id':str(i),'text':'invented','labels':{'label':label}} for i,label in enumerate(['a','b',None,None])]
    cfg=config_factory(items=items,responses={'0':'{"label":"a"}','1':'bad','2':'{"label":"b"}','3':''},
                       models=[{'id':mid,'provider':'mock','model':'canned','responses':file}
                               for mid,file in [('z','responses.json'),('<a>','other.json')]])
    (cfg.parent/'other.json').write_text(json.dumps({str(i):'{"label":"b"}' for i in range(4)}))
    directory=run(cfg); result=score(directory)
    field=result['models']['z']['fields']['label']
    assert field['counts']=={'total':4,'known_reference':2,'unknown_reference':2,'invalid_prediction':2,
                            'invalid_prediction_known_reference':1,'invalid_prediction_unknown_reference':1,'eligible':1}
    assert field['metrics']['exact_agreement']['value']==1
    assert field['failure_as_wrong']['exact_agreement']['value']==.5
    pair=result['pairwise'][0]
    assert pair['left_model_id']=='<a>' and pair['right_model_id']=='z'
    assert pair['fields']['label']['counts']['eligible']==2
    assert pair['fields']['label']['metrics']['exact_agreement']['value']==.5
    assert pair['fields']['label']['failure_as_wrong']['exact_agreement']['value']==.25
    manifest=read_json(directory/'manifest.json')
    manifest['models']=dict(reversed(list(manifest['models'].items())))
    write_json(directory/'manifest.json',manifest)
    assert score(directory)==result
    text=report(directory).read_text()
    assert '<a>' not in text and '&lt;a&gt;' in text
    assert '<script' not in text and 'Confusion matrix' in text and 'Input tokens' in text
    assert 'Format violation' in text


def test_missing_response_is_failure(config_factory):
    cfg=config_factory(); directory=run(cfg)
    response_path(directory,'m','one').unlink()
    model=score(directory)['models']['m']
    f=model['fields']['label']
    assert f['metrics']['exact_agreement']['value'] is None
    assert f['failure_as_wrong']['exact_agreement']['value']==0
    assert model['resources']['statuses']=={'not_requested':1}


def test_resources(config_factory):
    cfg=config_factory(responses={'one':{'text':'```json\n{"label":"a"}\n```','input_tokens':3,'output_tokens':2,'total_tokens':5}})
    res=score(run(cfg))['models']['m']['resources']
    assert res['tokens']['total_tokens']=={'total':5,'denominator':1}
    assert res['format_violations']=={'responses_with_violations':1,'denominator':1,'by_type':{'markdown_fence':1}}
    assert res['latency_seconds']['denominator']==1 and res['latency_seconds']['total']>=0


def test_cli(config_factory,capsys):
    cfg=config_factory()
    assert main(['run',str(cfg)])==0
    directory=cfg.parent/'run'
    assert main(['score',str(directory)])==0
    assert main(['report',str(directory)])==0
    assert (directory/'scores.json').is_file() and (directory/'report.html').is_file()
    assert main(['run',str(cfg.parent/'missing.yaml')])==1


def test_demo_offline(tmp_path):
    import shutil
    import yaml
    examples=Path(__file__).resolve().parents[1]/'examples'
    for file in examples.iterdir():
        if file.is_file(): shutil.copy(file,tmp_path/file.name)
    cfg=tmp_path/'demo.yaml'
    data=yaml.safe_load(cfg.read_text()); data['run_dir']='demo-run'; cfg.write_text(yaml.safe_dump(data))
    directory=run(cfg); s=score(directory)
    assert len(s['models'])==2 and len(s['pairwise'])==1
    assert all(m['resources']['completed']==12 for m in s['models'].values())
    assert report(directory).is_file()
