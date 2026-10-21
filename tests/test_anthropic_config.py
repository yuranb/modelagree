from pathlib import Path

import pytest
import yaml

from modelagree.config import load_config


def config(config_factory, parameters):
    return config_factory(models=[{'id': 'haiku', 'provider': 'anthropic',
                                   'model': 'claude-haiku-5-5', 'parameters': parameters}])


@pytest.mark.parametrize('parameters', [{}, {'effort': 'low'}])
def test_required_output_limit(config_factory, parameters):
    with pytest.raises(ValueError, match='requires parameters.max_output_tokens'):
        load_config(config(config_factory, parameters))


@pytest.mark.parametrize('value', [0, -1, True, 1.5, '2048', None])
def test_invalid_output_limit(config_factory, value):
    with pytest.raises(ValueError, match='positive integer'):
        load_config(config(config_factory, {'max_output_tokens': value}))


@pytest.mark.parametrize('key', ['temperature', 'top_p', 'top_k', 'seed',
                                'thinking', 'fallbacks', 'reasoning_effort', 'api_key'])
def test_unsupported_parameters(config_factory, key):
    with pytest.raises(ValueError, match='Unsupported provider parameters'):
        load_config(config(config_factory, {'max_output_tokens': 2048, key: 1}))


@pytest.mark.parametrize('value', ['none', 'minimal', 'HIGH', '', 1, None, [], {}])
def test_invalid_effort(config_factory, value):
    with pytest.raises(ValueError, match='Unsupported effort'):
        load_config(config(config_factory, {'max_output_tokens': 2048, 'effort': value}))


@pytest.mark.parametrize('effort', [None, 'low', 'medium', 'high', 'xhigh', 'max'])
def test_valid_parameters(config_factory, effort):
    parameters = {'max_output_tokens': 2048}
    if effort is not None:
        parameters['effort'] = effort
    frozen, _ = load_config(config(config_factory, parameters))
    assert frozen['models']['haiku']['parameters'] == parameters
    assert frozen['models']['haiku']['timeout_seconds'] == 60


def test_key_in_inputs_is_rejected(config_factory, monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'dummy-private-key')
    path = config(config_factory, {'max_output_tokens': 2048})
    (path.parent / 'prompt.txt').write_text('echo dummy-private-key')
    with pytest.raises(ValueError, match='Run inputs contain an environment API key'):
        load_config(path)


def test_crisismmd_example():
    examples = Path(__file__).resolve().parents[1] / 'examples'
    original = yaml.safe_load((examples / 'crisismmd.yaml').read_text())
    claude = yaml.safe_load((examples / 'crisismmd-claude.yaml').read_text())
    for key in ('dataset', 'prompt', 'label_schema', 'retry_attempts'):
        assert claude[key] == original[key]
    assert claude['run_dir'] == '../runs/crisismmd-claude'
    assert claude['models'] == [{'id': 'haiku', 'provider': 'anthropic',
        'model': 'claude-haiku-5-5', 'timeout_seconds': 60,
        'parameters': {'max_output_tokens': 2048, 'effort': 'low'}}]
