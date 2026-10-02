"""OpenAI Responses API using the standard library, without an SDK dependency."""
from .base import Response
from .http import post_json, token_count
from ..images import encoded_image
from ..security import require_key

URL='https://api.openai.com/v1/responses'


class OpenAIProvider:
    def __init__(self,model):
        require_key('OPENAI_API_KEY')
        self.timeout=model.get('timeout_seconds',60)

    def generate(self,request):
        parameters=dict(request['parameters'])
        effort=parameters.pop('reasoning_effort',None)
        content=[{'type':'input_text','text':request['text']}]
        if request.get('image'):
            info=request['image']
            content.append({'type':'input_image','image_url':f"data:{info['mime_type']};base64,{encoded_image(info)}"})
        body={**parameters,'model':request['model'],'instructions':request['prompt'],
              'input':[{'role':'user','content':content}],'store':False}
        if effort is not None:
            body['reasoning']={'effort':effort}
        data,raw=post_json(URL,body,{'Authorization':'Bearer '+require_key('OPENAI_API_KEY')},self.timeout)
        texts=[]
        output=data.get('output')
        for item in output if isinstance(output,list) else []:
            if not isinstance(item,dict) or item.get('type') != 'message': continue
            parts=item.get('content')
            for part in parts if isinstance(parts,list) else []:
                if not isinstance(part,dict): continue
                value=part.get('text') if part.get('type')=='output_text' else (
                    part.get('refusal') if part.get('type')=='refusal' else None)
                if isinstance(value,str): texts.append(value)
        usage=data.get('usage') or {}
        if not isinstance(usage,dict): usage={}
        return Response(''.join(texts), input_tokens=token_count(usage.get('input_tokens')),
                        output_tokens=token_count(usage.get('output_tokens')),
                        total_tokens=token_count(usage.get('total_tokens')),
                        raw_http_response=raw, api_request={'url':URL,'body':body})
