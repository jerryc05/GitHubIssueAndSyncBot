from math import floor
from pprint import pp
import subprocess as sp
import sys
import time

from config import APP_ID, PRIVATE_PEM_PATH

if __name__ == '__main__':
    while True:
        try:
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
            import jwt
            from requests import Session
            break
        except ImportError:
            input(
                'Install package [cryptography], [pyjwt], and [requests] now and press ENTER to continue! '
            )

    jwt_token = jwt.encode(
        {
            # issued at time, 60 seconds in the past to allow for clock drift
            'iat': floor(time.time()) - 60,
            # JWT expiration time (10 minute maximum)
            'exp': floor(time.time()) + 10*60,
            # GitHub App's identifier
            'iss': APP_ID},
        load_pem_private_key(open(PRIVATE_PEM_PATH, 'rb').read(), None),
        algorithm='RS256')

    sess = Session()
    sess.headers.clear()
    sess.headers.update({
        'Authorization': f'Bearer {jwt_token}',
        'User-Agent': ''})

    req = sess.get('https://api.github.com/app')
    pp(req.status_code)
    pp(req.json())
