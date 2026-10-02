import json

import pytest
from modelagree.schema import parse_response, validate_schema

SCHEMA = {'label': {'type':'categorical','labels':['a','b']},
          'rank': {'type':'ordinal','levels':['low','mid','high']},
          'tags': {'type':'multi_label','labels':['x','y']}}
VALID = '{"label":"a","rank":"mid","tags":["x"]}'


@pytest.mark.parametrize('value', ['1e999', '"\\ud800"', '[1e999,"\\ud800"]'])
def test_invalid_fields_are_serializable(value):
    parsed = parse_response('{"label":' + value + ',"rank":"mid","tags":[]}', SCHEMA)
    json.dumps(parsed, ensure_ascii=False, allow_nan=False).encode('utf-8')
    assert parsed['fields']['label'] == {'valid': False, 'value': None, 'error': 'unknown label'}
    assert parsed['fields']['rank']['valid'] and parsed['fields']['tags']['valid']


@pytest.mark.parametrize('text', ['', '   ', 'garbage', '{bad}', '{"label":', '[]', 'null',
                                  VALID + VALID, '{"label":"a","label":"b"}',
                                  '{"label":"a","extra":NaN}'])
def test_invalid_json_never_defaults(text):
    parsed=parse_response(text, SCHEMA)
    assert all(not v['valid'] for v in parsed['fields'].values())
    assert 'invalid_json' in parsed['format_violations']


@pytest.mark.parametrize('text,violation', [(VALID,None), ('```json\n'+VALID+'\n```','markdown_fence'),
                                          ('```\n'+VALID+'\n```','markdown_fence'),
                                          ('Here: '+VALID, 'surrounding_text'),
                                          (VALID+' done.', 'surrounding_text')])
def test_extract_single_object(text, violation):
    parsed=parse_response(text, SCHEMA)
    assert all(v['valid'] for v in parsed['fields'].values())
    assert parsed['format_violations'] == ([violation] if violation else [])


@pytest.mark.parametrize('text,field,reason', [
    ('{"label":"wrong","rank":"mid","tags":[]}', 'label','unknown label'),
    ('{"label":"a","rank":1,"tags":[]}', 'rank','unknown label'),
    ('{"label":"a","rank":"mid","tags":["x","x"]}', 'tags','duplicate label'),
    ('{"label":"a","rank":"mid","tags":["z"]}', 'tags','unknown label'),
    ('{"label":"a","rank":"mid","tags":"x"}', 'tags','expected a list'),
    ('{"label":"a","rank":"mid"}', 'tags','missing field'),
])
def test_fields_are_independent(text, field, reason):
    parsed=parse_response(text,SCHEMA)
    assert not parsed['fields'][field]['valid']
    assert parsed['fields'][field]['error']==reason
    assert all(v['valid'] for k,v in parsed['fields'].items() if k != field)


def test_extra_fields_flagged_and_empty_set_valid():
    p=parse_response('{"label":"a","rank":"mid","tags":[],"other":1}',SCHEMA)
    assert p['format_violations']==['extra_fields']
    assert p['fields']['tags']['valid'] and p['fields']['tags']['value']==[]


@pytest.mark.parametrize('schema', [{}, {'x':{'type':'bad','labels':['a']}},
                                    {'x':{'type':'categorical','labels':['a','a']}},
                                    {'x':{'type':'ordinal','labels':['a']}},
                                    {'x':{'type':'categorical','labels':[1]}}])
def test_invalid_schema(schema):
    with pytest.raises(ValueError): validate_schema(schema)
