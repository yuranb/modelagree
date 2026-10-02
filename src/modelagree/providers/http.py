"""Small synchronous HTTPS transport; never logs headers or error bodies."""
import http.client
import json
import ssl
from urllib import error, request

from .base import ProviderError
from ..security import redact


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError('redirect_not_allowed')


def open_request(req, timeout):
    # Explicitly prevent credential-bearing requests from following redirects.
    return request.build_opener(NoRedirect()).open(req, timeout=timeout)


def post_json(url, body, headers, timeout):
    req=request.Request(url, data=json.dumps(body,ensure_ascii=False,allow_nan=False).encode('utf-8'),
                        headers={'Content-Type':'application/json',**headers}, method='POST')
    try:
        with open_request(req, timeout) as response:
            raw=redact(response.read().decode('utf-8',errors='replace'))
    except error.HTTPError as exc:
        code=exc.code
        exc.close()
        raise ProviderError(f'http_{code}', code in {408,429} or 500 <= code <= 599) from None
    except (TimeoutError,):
        raise ProviderError('timeout',True) from None
    except ssl.SSLError:
        raise ProviderError('tls_error') from None
    except error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLError):
            raise ProviderError('tls_error') from None
        raise ProviderError('timeout' if isinstance(exc.reason,TimeoutError) else 'connection_error',True) from None
    except (ConnectionError, OSError, http.client.HTTPException):
        raise ProviderError('connection_error',True) from None
    try:
        data=json.loads(raw)
    except ValueError:
        data={}
    return data if isinstance(data,dict) else {}, raw


def token_count(value):
    return value if type(value) is int and value >= 0 else None
