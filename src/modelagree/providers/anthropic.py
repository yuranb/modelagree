"""Anthropic Messages API with explicit output limits and no fallbacks."""
from .base import Response
from .http import post_json, token_count
from ..images import encoded_image
from ..security import require_key


class AnthropicProvider:
    def __init__(self, model):
        require_key('ANTHROPIC_API_KEY')
        self.timeout = model.get('timeout_seconds', 60)

    def generate(self, request):
        content = [{'type': 'text', 'text': request['text']}]
        if request.get('image'):
            info = request['image']
            content.append({'type': 'image', 'source': {'type': 'base64',
                            'media_type': info['mime_type'], 'data': encoded_image(info)}})
        parameters = request['parameters']
        body = {'model': request['model'], 'max_tokens': parameters['max_output_tokens'],
                'system': request['prompt'], 'messages': [{'role': 'user', 'content': content}]}
        if 'effort' in parameters:
            body['output_config'] = {'effort': parameters['effort']}
        url = 'https://api.anthropic.com/v1/messages'
        data, raw = post_json(url, body, {'x-api-key': require_key('ANTHROPIC_API_KEY'),
                                        'anthropic-version': '2023-06-01'}, self.timeout)
        blocks = data.get('content')
        text = ''.join(block['text'] for block in (blocks if isinstance(blocks, list) else [])
                       if isinstance(block, dict) and block.get('type') == 'text'
                       and isinstance(block.get('text'), str))
        usage = data.get('usage')
        if not isinstance(usage, dict): usage = {}
        return Response(text, input_tokens=token_count(usage.get('input_tokens')),
                        output_tokens=token_count(usage.get('output_tokens')), total_tokens=None,
                        raw_http_response=raw, api_request={'url': url, 'body': body})
