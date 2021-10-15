#!/usr/bin/env python3

from datetime import datetime
from locale import LC_TIME, getlocale, setlocale
from math import floor
from os import environ
from pathlib import Path
from pprint import pp
import sqlite3
import sys
import time
import typing as t
from urllib.parse import quote_plus

OWNER = environ.get('OWNER', '').strip()
REPO = environ.get('REPO', '').strip()
INSTALL_ID = int(environ.get('INSTALL_ID', '0'))
APP_ID = int(environ.get('APP_ID', '0'))
PRIVATE_PEM_PATH = environ.get('PRIVATE_PEM_PATH', '').strip()

DB_PATH = Path(__file__).parent / 'db.db'
DB_SCHEMA_PATH = Path(__file__).parent / 'schema.sql'

JWT_TABLE_NAME = 'jwt_auth'
ACC_TABLE_NAME = 'acc_auth'

ISSUES_TABLE_NAME = 'issues'
ISSUES_SUB_ROW_NAME = '_sub'

TIME_FMT = r'%Y-%m-%d %H:%M:%S %Z%z, %A'

private_pem_path = Path(PRIVATE_PEM_PATH)


def self_check():
    for val, name in ((OWNER, 'OWNER'), \
                      (REPO, 'REPO'), \
                      (INSTALL_ID, 'INSTALL_ID'), \
                      (APP_ID, 'APP_ID'), \
                      (PRIVATE_PEM_PATH, 'PRIVATE_PEM_PATH')):
        if not val:
            print(f'{name} not set in env var!')
            exit(1)

    global private_pem_path
    if not private_pem_path.is_file() and not private_pem_path.is_absolute():
        private_pem_path = Path(__file__).parent / PRIVATE_PEM_PATH

    if not private_pem_path.is_file():
        raise FileNotFoundError(
            f'PRIVATE_PEM_PATH=[{PRIVATE_PEM_PATH}] not found!')

    try:
        global load_pem_private_key, jwt, Session, timezone, utc
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        import jwt
        from requests import Session
        from pytz import timezone, utc
    except ImportError:
        print('Some packages missing! Install packages according to [requirements.txt] and restart!')
        exit(1)


def init_db():
    global db
    db = sqlite3.connect(DB_PATH, isolation_level=None)
    db.executescript(open(DB_SCHEMA_PATH).read())


def get_db():
    global db
    init_db()
    return db


def get_jwt(cached: bool = True) -> str:
    db_f = Path(__file__).parent / DB_PATH
    token = ''

    if cached:
        if not db_f.exists():
            cached = False
        else:
            if not get_db().execute(
                    f'select 1 from {JWT_TABLE_NAME} limit 1').fetchone():
                cached = False
            else:
                exp_time, token = get_db().execute(
                    f'select exp_time,token from {JWT_TABLE_NAME} limit 1'
                ).fetchone()
                cached = time.time() < exp_time and not not token

    if not cached:
        print('Regenerating JWT token!')
        dur = 60
        exp_time = floor(time.time()) + dur
        token = str(
            jwt.encode(
                {
                    # issued at time, 60 seconds in the past to allow for clock drift
                    'iat': exp_time - dur - 60,
                    # JWT expiration time (10 minute maximum)
                    'exp': exp_time,
                    # GitHub App's identifier
                    'iss': APP_ID},
                load_pem_private_key(
                    open(private_pem_path, 'rb').read(), None),
                algorithm='RS256'))

        if get_db().execute(
                f'select 1 from {JWT_TABLE_NAME} limit 1').fetchone():
            get_db().execute(f'delete from {JWT_TABLE_NAME}')
        get_db().execute(
            f'insert into {JWT_TABLE_NAME}(exp_time,token) values(?,?)',
            (exp_time, token))

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
    self_check()

    db_f = Path(__file__).parent / DB_PATH
    retry = True
    token = ''

    if cached:
        if not db_f.exists():
            cached = False
        else:
            if not get_db().execute(
                    f'select 1 from {ACC_TABLE_NAME} limit 1').fetchone():
                cached = False
            else:
                exp_time, token = get_db().execute(
                    f'select exp_time,token from {ACC_TABLE_NAME} limit 1'
                ).fetchone()
                cached = time.time() < exp_time and not not token

    if not cached:
        print('Regenerating ACCESS token!')
        while True:
            req = new_sess(jwt=True).post(
                f'https://api.github.com/app/installations/{INSTALL_ID}/access_tokens'
            )
            if retry and req.status_code == 401:
                print('JWT token expired!')
                get_jwt(cached=False)
                retry = False
            else:
                if not req.ok:
                    pp(req.json())
                    req.raise_for_status()
                exp_time = int(
                    datetime.strptime(req.json()['expires_at'],
                                      r'%Y-%m-%dT%H:%M:%SZ').timestamp())
                token = req.json()['token']

                if get_db().execute( \
                        f'select 1 from {ACC_TABLE_NAME} limit 1').fetchone():
                    get_db().execute(f'delete from {ACC_TABLE_NAME}')
                get_db().execute(
                    f'insert into {ACC_TABLE_NAME}(exp_time,token) values(?,?)',
                    (exp_time, token))
                break

    return token


def send_api(method: str,
             url: str,
             jwt: bool,
             acc_tok: bool,
             js: 'dict[str, object]|None' = None) -> 'dict[str,object]':

    retry = True
    while True:
        req = new_sess(jwt=jwt, acc_tok=acc_tok).request(method,
                                                         url,
                                                         json=js,
                                                         timeout=60)
        if retry and req.status_code == 401:
            print('ACCESS token expired!')
            get_inst_acc_tok(cached=False)
            retry = False
        else:
            if not req.ok:
                pp(req.json())
                req.raise_for_status()
            return req.json()


def get_api(url: str, jwt: bool = False, acc_tok: bool = True):
    return send_api('GET', url, jwt=jwt, acc_tok=acc_tok)


def post_api(url: str,
             js: 'dict[str, object]|None',
             jwt: bool = False,
             acc_tok: bool = True):
    return send_api('POST', url, jwt=jwt, acc_tok=acc_tok, js=js)


def create_issue(title: 'str|int',
                 body: 'str|None' = None,
                 milestone: 'str|int|None' = None,
                 labels: 'list[str]|None' = None,
                 assignees: 'list[str]|None' = None):

    labels = list(set((labels if labels else []) + ['bot']))
    js: 'dict[str, object]' = {'title': title, 'labels': labels}

    for val, name in ((body, 'body'), \
                      (milestone, 'milestone'), \
                      (assignees, 'assignees')):
        if val:
            js[name] = val

    return post_api(f'https://api.github.com/repos/{OWNER}/{REPO}/issues', js)


def search_open_issue(title: 'str'):
    q = f'is:issue is:open in:title repo:{OWNER}/{REPO} {title[:256]}'
    return get_api(
        f'https://api.github.com/search/issues?q={quote_plus(q)}&per_page=100'
        # TODO &page=1 ...
    )


def create_comment(issue_id: int, body: 'str'):
    return post_api(
        f'https://api.github.com/repos/{OWNER}/{REPO}/issues/{issue_id}/comments',
        {'body': body})


class Issue:

    def __init__(self, rowid: int, title: str, body: 'str|None',
                 milestone: 'str|None', labels: 'list[str]|None',
                 assignees: 'list[str]|None', unix_epoch: int) -> None:
        self.rowid = rowid
        self.title = title
        self._body = body
        self.milestone = milestone
        self.labels = labels
        self.assignees = assignees
        self.unix_epoch = unix_epoch

    def body(self) -> str:
        body = self._body if self._body else ''

        dt = datetime.utcfromtimestamp(self.unix_epoch).replace(tzinfo=utc)
        loc = getlocale(LC_TIME)
        body += (
            '\n\n'
            '---\n'
            'Time happened:\n'
            '|Timezone|Time|\n'
            '|-:|:-|\n'
            f'|UTC|`{dt.strftime(TIME_FMT)}`|\n'
            f'|US/Eastern|`{setlocale(LC_TIME, "en_US") and dt.astimezone(timezone("US/Eastern")).strftime(TIME_FMT)}`|\n'
            f'|Asia/Shanghai|`{setlocale(LC_TIME, "zh_CN") and dt.astimezone(timezone("Asia/Shanghai")).strftime(TIME_FMT)}`|\n'
        )
        setlocale(LC_TIME, loc)
        return body


def check_and_submit():
    for issue_ in get_db().execute(
            'select title,body,milestone,labels,assignees,rowid,unix_epoch '
            f'from {ISSUES_TABLE_NAME} where {ISSUES_SUB_ROW_NAME}=0'  # todo resend after 3 min timeout
    ).fetchall():
        issue = Issue(
            title=issue_[0],
            body=issue_[1],
            milestone=issue_[2],
            labels=[x.strip() for x in t.cast(str, issue_[3]).split('\n')]
            if issue_[3] else None,
            assignees=[x.strip() for x in t.cast(str, issue_[4]).split('\n')]
            if issue_[4] else None,
            rowid=issue_[5],
            unix_epoch=issue_[6])

        get_db().execute(
            f'update {ISSUES_TABLE_NAME} set {ISSUES_SUB_ROW_NAME}=? where rowid=?',
            (-1, issue.rowid))
        for search in t.cast('list[dict[str, object]]',
                             search_open_issue(issue.title)['items']):
            if search['title'] == issue.title:
                create_comment(t.cast(int, search['id']), issue.body())
                break
        else:
            create_issue(issue.title, issue.body(), issue.milestone,
                         issue.labels, issue.assignees)
        get_db().execute(f'delete from {ISSUES_TABLE_NAME} where rowid=?',
                         (issue.rowid, ))
        print('Submitted!')


if __name__ == '__main__':
    self_check()

    if '-i' in sys.argv or '--init' in sys.argv:
        init_db()
    elif '-c' in sys.argv or '--check' in sys.argv:
        self_check()
    else:
        check_and_submit()
