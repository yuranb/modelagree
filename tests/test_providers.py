import base64
import io
import json
import ssl
from urllib.error import HTTPError, URLError

import pytest

from modelagree import runner
from modelagree.images import image_info
from modelagree.providers import create_provider
from modelagree.providers import http
from modelagree.providers.base import ProviderError
from modelagree.storage import read_json, response_path


@pytest.fixture
def mocked_http(monkeypatch):
    calls=[]
    responses=[]
    def open_request(request, timeout):
        calls.append((request,timeout))
        value=responses.pop(0)
        if isinstance(value,Exception): raise value
        return io.BytesIO(value if isinstance(value,bytes) else json.dumps(value).encode())
    monkeypatch.setattr(http,'open_request',open_request)
    return calls,responses


def model(provider, parameters=None):
    return {'id':provider,'provider':provider,'model':'test-model','parameters':parameters or {},'timeout_seconds':7}


def request(provider, parameters=None, image=None):
    return {**model(provider,parameters),'item_id':'one','text':'Invented image context.',
            'prompt':'Frozen prompt.','image':image}


def envelope(provider, text='{"label":"a"}'):
    if provider=='openai':
        return {'status':'completed','output':[{'type':'reasoning','summary':[]},
                 {'type':'message','content':[{'type':'output_text','text':text}]}],
                'usage':{'input_tokens':7,'output_tokens':3,'total_tokens':10}}
    return {'candidates':[{'content':{'parts':[{'text':'ignored thinking','thought':True},{'text':text}]},'finishReason':'STOP'}],
            'usageMetadata':{'promptTokenCount':7,'candidatesTokenCount':3,'totalTokenCount':10}}


@pytest.mark.parametrize('provider',['openai','gemini'])
@pytest.mark.parametrize('with_image',[False,True])
def test_text_and_image_request_shape(provider,with_image,mocked_http,monkeypatch,tiny_image):
    calls,responses=mocked_http
    variable=provider.upper()+'_API_KEY'
    monkeypatch.setenv(variable,'dummy-test-credential')
    parameters={'temperature':.2,'top_p':.8,'max_output_tokens':200}
    responses.append(envelope(provider))
    req=request(provider,parameters,image_info(tiny_image) if with_image else None)
    result=create_provider(model(provider)).generate(req)
    assert result.text=='{"label":"a"}' and result.total_tokens==10
    assert result.input_tokens==7 and result.output_tokens==3
    assert len(calls)==1
    wire,timeout=calls[0]
    body=json.loads(wire.data)
    assert timeout==7 and wire.method=='POST'
    assert 'dummy-test-credential' not in result.raw_http_response
    assert 'dummy-test-credential' not in json.dumps(result.api_request)
    if provider=='openai':
        assert wire.full_url=='https://api.openai.com/v1/responses'
        assert wire.get_header('Authorization')=='Bearer dummy-test-credential'
        assert body['instructions']=='Frozen prompt.' and body['store'] is False
        assert body['max_output_tokens']==200
        parts=body['input'][0]['content']
        assert parts[0]=={'type':'input_text','text':'Invented image context.'}
        if with_image:
            assert parts[1]['image_url'].startswith('data:image/png;base64,')
            assert base64.b64decode(parts[1]['image_url'].split(',',1)[1])==tiny_image.read_bytes()
    else:
        assert wire.full_url.endswith('/test-model:generateContent') and '?' not in wire.full_url
        assert wire.get_header('X-goog-api-key')=='dummy-test-credential'
        assert body['systemInstruction']['parts']==[{'text':'Frozen prompt.'}]
        assert body['generationConfig']=={'candidateCount':1,'temperature':.2,'topP':.8,'maxOutputTokens':200}
        parts=body['contents'][0]['parts']
        assert parts[0]=={'text':'Invented image context.'}
        if with_image:
            assert parts[1]['inlineData']['mimeType']=='image/png'
            assert base64.b64decode(parts[1]['inlineData']['data'])==tiny_image.read_bytes()
    assert len(parts)==(2 if with_image else 1)


def test_reasoning_and_gemini_model_prefix(mocked_http,monkeypatch):
    calls,responses=mocked_http
    monkeypatch.setenv('OPENAI_API_KEY','dummy-openai')
    monkeypatch.setenv('GEMINI_API_KEY','dummy-gemini')
    responses.extend([envelope('openai'),envelope('gemini')])
    create_provider(model('openai')).generate(request('openai',{'reasoning_effort':'low'}))
    assert json.loads(calls[0][0].data)['reasoning']=={'effort':'low'}
    req=request('gemini',{'seed':2,'top_k':3}); req['model']='models/test-model'
    create_provider(model('gemini')).generate(req)
    assert '/models/models/' not in calls[1][0].full_url
    assert json.loads(calls[1][0].data)['generationConfig']['topK']==3


@pytest.mark.parametrize('status,retryable',[(400,False),(401,False),(403,False),(404,False),
                                          (408,True),(429,True),(500,True),(502,True),(503,True),(599,True)])
def test_http_errors_are_classified_without_leaking_details(status,retryable,mocked_http):
    calls,responses=mocked_http
    responses.append(HTTPError('https://example.invalid',status,'secret-body-and-key',{},io.BytesIO(b'secret')))
    with pytest.raises(ProviderError) as error:
        http.post_json('https://example.invalid',{}, {},1)
    assert error.value.retryable is retryable
    assert str(error.value)==f'http_{status}' and error.value.__suppress_context__


@pytest.mark.parametrize('failure,code,retryable',[(TimeoutError('secret'),'timeout',True),
    (URLError(TimeoutError('secret')),'timeout',True),
    (URLError('secret'),'connection_error',True),
    (ConnectionResetError('secret'),'connection_error',True),
    (ssl.SSLError('secret'),'tls_error',False),
    (URLError(ssl.SSLError('secret')),'tls_error',False)])
def test_transport_errors(failure,code,retryable,mocked_http):
    _,responses=mocked_http; responses.append(failure)
    with pytest.raises(ProviderError) as error:
        http.post_json('https://example.invalid',{}, {},1)
    assert error.value.code==code and error.value.retryable is retryable


def test_redirects_cannot_forward_credentials():
    with pytest.raises(ProviderError,match='redirect_not_allowed'):
        http.NoRedirect().redirect_request(None,None,307,'redirect',{},'https://elsewhere.invalid')


@pytest.mark.parametrize('provider',['openai','gemini'])
def test_missing_key_fails_before_http(provider,mocked_http):
    with pytest.raises(ValueError,match=provider.upper()+'_API_KEY'):
        create_provider(model(provider))
    assert mocked_http[0]==[]


@pytest.mark.parametrize('provider',['openai','gemini'])
@pytest.mark.parametrize('raw',[b'not an API JSON response',b'{}'])
def test_successful_http_without_model_text_is_preserved(provider,raw,mocked_http,monkeypatch,config_factory):
    calls,responses=mocked_http; responses.append(raw)
    monkeypatch.setenv(provider.upper()+'_API_KEY','test-unused-key')
    cfg=config_factory(models=[model(provider)])
    directory=runner.run(cfg); path=response_path(directory,provider,'one')
    record=read_json(path)
    assert record['raw_http_response']==raw.decode() and record['raw_response']==''
    assert record['status']=='completed' and not record['parsed']['fields']['label']['valid']
    before=path.read_bytes(); runner.run(cfg)
    assert len(calls)==1 and path.read_bytes()==before


@pytest.mark.parametrize('provider',['openai','gemini'])
def test_mocked_http_retry_then_invalid_completion_is_never_retried(provider,mocked_http,monkeypatch,config_factory):
    calls,responses=mocked_http
    monkeypatch.setenv(provider.upper()+'_API_KEY','dummy-private-key')
    monkeypatch.setattr(runner.time,'sleep',lambda n:None)
    responses.extend([HTTPError('https://example.invalid',429,'dummy-private-key',{},io.BytesIO()),
                      envelope(provider,'invalid output')])
    cfg=config_factory(models=[model(provider)]); directory=runner.run(cfg)
    record=read_json(response_path(directory,provider,'one'))
    assert record['status']=='completed' and len(record['attempts'])==2
    assert record['attempts'][0]['error']=='http_429'
    assert record['raw_response']=='invalid output'
    runner.run(cfg); assert len(calls)==2
    for path in directory.rglob('*.json'):
        assert 'dummy-private-key' not in path.read_text()


def test_refusal_preserved_without_retry(mocked_http,monkeypatch,config_factory):
    monkeypatch.setenv('OPENAI_API_KEY','dummy-key')
    calls,responses=mocked_http
    responses.append({'output':[{'type':'message','content':[{'type':'refusal','refusal':'Cannot label.'}]}]})
    cfg=config_factory(models=[model('openai')]); directory=runner.run(cfg); runner.run(cfg)
    rec=read_json(response_path(directory,'openai','one'))
    assert rec['raw_response']=='Cannot label.' and rec['usage']['total_tokens'] is None
    assert len(calls)==1


def test_echoed_key_is_redacted_from_raw_envelope_and_saved_text(mocked_http,monkeypatch,config_factory):
    monkeypatch.setenv('OPENAI_API_KEY','dummy-private-key')
    mocked_http[1].append(envelope('openai','echo dummy-private-key'))
    cfg=config_factory(models=[model('openai')]); directory=runner.run(cfg)
    for path in directory.rglob('*.json'):
        assert 'dummy-private-key' not in path.read_text()
    assert read_json(response_path(directory,'openai','one'))['raw_response']=='echo [REDACTED_API_KEY]'


def test_completed_real_response_can_resume_without_a_key(mocked_http,monkeypatch,config_factory):
    monkeypatch.setenv('OPENAI_API_KEY','dummy-credential')
    calls,responses=mocked_http; responses.append(envelope('openai'))
    cfg=config_factory(models=[model('openai')]); directory=runner.run(cfg)
    path=response_path(directory,'openai','one'); original=path.read_bytes()
    monkeypatch.delenv('OPENAI_API_KEY')
    runner.run(cfg)
    assert len(calls)==1 and path.read_bytes()==original


def test_invalid_credential_cannot_leak_in_an_http_exception(monkeypatch,mocked_http):
    monkeypatch.setenv('OPENAI_API_KEY','secret\ninvalid-header')
    with pytest.raises(ValueError) as exc:
        create_provider(model('openai'))
    assert 'secret' not in str(exc.value) and not mocked_http[0]
