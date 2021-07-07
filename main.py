from math import floor
from pathlib import Path
from pprint import pp
import time

from config import APP_ID, PRIVATE_PEM_PATH


def get_token() -> str:
    token_f = Path(__file__).parent / '.token-info.cfg'
    cached = False
    token = ''

    if token_f.exists():
        with open(token_f, 'r') as f:
            exp_time, token = int(
                f'0{f.readline().strip()}'), f.readline().strip()
        cached = time.time() < exp_time and token

    if not cached:
        dur = 60
        exp_time = floor(time.time()) + dur
        token: str = jwt.encode(
            {
                # issued at time, 60 seconds in the past to allow for clock drift
                'iat': exp_time - dur - 60,
                # JWT expiration time (10 minute maximum)
                'exp': exp_time,
                # GitHub App's identifier
                'iss': APP_ID},
            load_pem_private_key(open(PRIVATE_PEM_PATH, 'rb').read(), None),
            algorithm='RS256')

        with open(token_f, 'w') as f:
            f.write(str(exp_time))
            f.write('\n')
            f.write(token)

    return token


if __name__ == '__main__':
    if not Path(PRIVATE_PEM_PATH).exists():
        raise FileNotFoundError(
            f'PRIVATE_PEM_PATH=[{PRIVATE_PEM_PATH}] not found!')

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

    sess = Session()
    sess.headers.clear()
    sess.headers.update({
        'Authorization': f'Bearer {get_token()}',
        'User-Agent': ''})

    req = sess.get('https://api.github.com/app')
    pp(req.status_code)
    pp(req.json())
