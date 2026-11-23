"""Bounded one-variable gateway probes; never persist credentials or raw headers."""
import argparse
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

from sciforge_review.llm import load_config, _headers, _extract_text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    c = load_config()
    base = {'model': c.model, 'input': 'Reply with ok.', 'max_output_tokens': 64}
    probes = [
        ('baseline', '/responses', dict(base), True),
        ('omit_actor', '/responses', dict(base), False),
        ('structured_input', '/responses', {**base, 'input': [
            {'role': 'user', 'content': [{'type': 'input_text', 'text': 'Reply with ok.'}]}]}, True),
        ('chat_endpoint_schema', '/chat/completions', {
            'model': c.model, 'messages': [{'role': 'user', 'content': 'Reply with ok.'}],
            'max_completion_tokens': 64}, True),
    ]
    rows = []
    for name, endpoint, payload, actor in probes:
        headers = _headers(c)
        if not actor:
            headers.pop('x-openai-actor-authorization', None)
        req = urllib.request.Request(c.base_url + endpoint,
                                     data=json.dumps(payload).encode(), headers=headers)
        row = {'probe': name, 'endpoint': endpoint, 'model': c.model,
               'actor_header_present': actor, 'payload': payload}
        start = time.monotonic()
        try:
            try:
                response = urllib.request.urlopen(req, timeout=25)
            except urllib.error.HTTPError as exc:
                response = exc
            with response:
                row['status'] = response.code
                body = json.loads(response.read(100000).decode())
            error = body.get('error', {})
            if isinstance(error, dict):
                row['error_type'] = str(error.get('type', ''))[:100]
                message = str(error.get('message', ''))
                for secret in [c.api_key, c.bearer_token]:
                    if secret:
                        message = message.replace(secret, '[REDACTED]')
                # Persist only known gateway diagnostics, never arbitrary echoed data.
                row['known_upstream_forbidden'] = 'Upstream access forbidden' in message
            text = _extract_text(body)
            if endpoint == '/chat/completions':
                choices = body.get('choices', [])
                text = choices[0].get('message', {}).get('content', '') if choices else ''
            row['has_generated_text'] = bool(text)
        except Exception as exc:
            row['exception_type'] = type(exc).__name__
        row['seconds'] = time.monotonic()-start
        rows.append(row)
        (args.out/'probes.json').write_text(json.dumps(rows, indent=2))
        print(name, row.get('status'), row.get('exception_type', ''),
              'text=' + str(row.get('has_generated_text', False)), flush=True)


if __name__ == '__main__':
    main()
