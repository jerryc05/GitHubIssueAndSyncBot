from datetime import datetime
from math import floor
from pathlib import Path
from pprint import pp
import time

from config import OWNER, REPO, INSTALL_ID, APP_ID, PRIVATE_PEM_PATH

CONFIG_FILENAME = 'config.py'
JWT_FILENAME = '.jwt-token.cfg'
ACC_TOK_FILENAME = '.acc-token.cfg'


def self_check():
    if not Path(PRIVATE_PEM_PATH).exists():
        raise FileNotFoundError(
            f'PRIVATE_PEM_PATH=[{PRIVATE_PEM_PATH}] not found!')
    for val, name in ((OWNER, 'OWNER'), \
                      (REPO, 'REPO'), \
                      (INSTALL_ID, 'INSTALL_ID'), \
                      (APP_ID, 'APP_ID')):
        if not val:
            print(f'{name} not set in {CONFIG_FILENAME}!')
            exit(1)

    while True:
        try:
            global load_pem_private_key, jwt, Session
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
            import jwt
            from requests import Session
            break
        except ImportError:
            input(
                'Install package [cryptography], [pyjwt], and [requests] now and press ENTER to continue! '
            )


def get_jwt(cached: bool = True) -> str:
    token_f = Path(__file__).parent / JWT_FILENAME
    token = ''

    if cached:
        if not token_f.exists():
            cached = False
        else:
            with open(token_f, 'r') as f:
                exp_time, token = int(
                    f'0{f.readline().strip()}'), f.readline().strip()
            cached = time.time() < exp_time and not not token

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


def new_sess(jwt: bool = False, acc_tok: bool = False):
    sess = Session()
    sess.headers.clear()
    sess.headers['User-Agent'] = 'bot'
    if jwt:
        sess.headers['Authorization'] = f'Bearer {get_jwt()}'
    if acc_tok:
        sess.headers['Authorization'] = f'token {get_inst_acc_tok()}'
    return sess


def get_inst_acc_tok(cached: bool = True) -> str:
    token_f = Path(__file__).parent / ACC_TOK_FILENAME
    retry = True
    token = ''

    if cached:
        if not token_f.exists():
            cached = False
        else:
            with open(token_f, 'r') as f:
                exp_time, token = int(
                    f'0{f.readline().strip()}'), f.readline().strip()
            cached = time.time() < exp_time and not not token

    if not cached:
        while True:
            req = new_sess(jwt=True).post(
                f'https://api.github.com/app/installations/{INSTALL_ID}/access_tokens'
            )
            if retry and req.status_code == 401:
                get_jwt(cached=False)
                retry = False
            else:
                req.raise_for_status()
                exp_time = int(
                    datetime.strptime(req.json()['expires_at'],
                                      '%Y-%m-%dT%H:%M:%SZ').timestamp())
                token = req.json()['token']
                with open(token_f, 'w') as f:
                    f.write(str(exp_time))
                    f.write('\n')
                    f.write(token)
                break

    return token


if __name__ == '__main__':
    self_check()

    req = new_sess(acc_tok=True).post(
        f'https://api.github.com/repos/{OWNER}/{REPO}/issues',
        json={'title': 'issue test title'})
    pp(f'{req.request.method} {req.request.url}')
    pp(req.status_code)
    pp(req.json())
