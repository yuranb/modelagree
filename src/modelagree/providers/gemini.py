"""Gemini generateContent API, with one candidate per item."""
from urllib.parse import quote

from .base import Response
from .http import post_json, token_count
from ..images import encoded_image
from ..security import require_key

PARAMETERS={'temperature':'temperature','top_p':'topP','top_k':'topK',
            'max_output_tokens':'maxOutputTokens','seed':'seed'}


class GeminiProvider:
    def __init__(self,model):
        require_key('GEMINI_API_KEY')
        self.timeout=model.get('timeout_seconds',60)

    def generate(self,request):
        parts=[{'text':request['text']}]
        if request.get('image'):
            info=request['image']
            parts.append({'inlineData':{'mimeType':info['mime_type'],'data':encoded_image(info)}})
        body={'systemInstruction':{'parts':[{'text':request['prompt']}]},
              'contents':[{'role':'user','parts':parts}],
              'generationConfig':{'candidateCount':1,**{PARAMETERS[k]:v for k,v in request['parameters'].items()}}}
        model=request['model'].removeprefix('models/')
        url=f'https://generativelanguage.googleapis.com/v1beta/models/{quote(model,safe="")}:generateContent'
        data,raw=post_json(url,body,{'x-goog-api-key':require_key('GEMINI_API_KEY')},self.timeout)
        candidates=data.get('candidates')
        first=candidates[0] if isinstance(candidates,list) and candidates and isinstance(candidates[0],dict) else {}
        content=first.get('content') or {}
        if not isinstance(content,dict): content={}
        parts=content.get('parts')
        text=''.join(p['text'] for p in (parts if isinstance(parts,list) else [])
                     if isinstance(p,dict) and isinstance(p.get('text'),str) and not p.get('thought',False))
        usage=data.get('usageMetadata') or {}
        if not isinstance(usage,dict): usage={}
        return Response(text,input_tokens=token_count(usage.get('promptTokenCount')),
                        output_tokens=token_count(usage.get('candidatesTokenCount')),
                        total_tokens=token_count(usage.get('totalTokenCount')),
                        raw_http_response=raw,api_request={'url':url,'body':body})
