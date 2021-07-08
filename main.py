#!/usr/bin/env python3

from dataclasses import dataclass
from datetime import datetime
from locale import LC_TIME, getlocale, setlocale
from math import floor
from pathlib import Path
from pprint import pp
import sqlite3
import time
import typing as t
from urllib.parse import quote_plus

from config import OWNER, REPO, INSTALL_ID, APP_ID, PRIVATE_PEM_PATH

CONFIG_FILENAME = 'config.py'
DB_FILENAME = 'db.db'
DB_SCHEMA_FILENAME = 'schema.sql'

JWT_TABLE_NAME = 'jwt_auth'
ACC_TABLE_NAME = 'acc_auth'

ISSUES_TABLE_NAME = 'issues'
ISSUES_SUB_ROW_NAME = '_sub'


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

    try:
        global load_pem_private_key, jwt, Session, timezone, utc
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        import jwt
        from requests import Session
        from pytz import timezone, utc
    except ImportError:
        print('Install these packages before running this:\n'
              '1. cryptography\n'
              '2. pyjwt\n'
              '3. requests\n'
              '4. pytz')
        exit(1)


def get_db():
    global db
    if 'db' not in globals():
        db = sqlite3.connect(DB_FILENAME, isolation_level=None)
        db.executescript(open(DB_SCHEMA_FILENAME).read())
    return db


def get_jwt(cached: bool = True) -> str:
    db_f = Path(__file__).parent / DB_FILENAME
    token = ''

    if cached:
        if not db_f.exists():
            cached = False
        else:
            if not get_db().execute(
                    f'select count(*) from {JWT_TABLE_NAME}').fetchone()[0]:
                cached = False
            else:
                exp_time, token = get_db().execute(
                    f'select exp_time,token from {JWT_TABLE_NAME}').fetchone()
                cached = time.time() < exp_time and not not token

    if not cached:
        print('Regenerating JWT token!')
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

        if get_db().execute(
                f'select count(*) from {JWT_TABLE_NAME}').fetchone()[0]:
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
    db_f = Path(__file__).parent / DB_FILENAME
    retry = True
    token = ''

    if cached:
        if not db_f.exists():
            cached = False
        else:
            if not get_db().execute(
                    f'select count(*) from {ACC_TABLE_NAME}').fetchone()[0]:
                cached = False
            else:
                exp_time, token = get_db().execute(
                    f'select exp_time,token from {ACC_TABLE_NAME}').fetchone()
                cached = time.time() < exp_time and not not token

    if not cached:
        print('Regenerating ACCESS token!')
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
                                      r'%Y-%m-%dT%H:%M:%SZ').timestamp())
                token = req.json()['token']

                if get_db().execute( \
                        f'select count(*) from {ACC_TABLE_NAME}').fetchone()[0]:
                    get_db().execute(f'delete from {ACC_TABLE_NAME}')
                get_db().execute(
                    f'insert into {ACC_TABLE_NAME}(exp_time,token) values(?,?)',
                    (exp_time, token))
                break

    return token


def send_api(method: str,
             url: str,
             js: 'dict[str, object]|None' = None) -> 'dict[str,object]':

    retry = True
    while True:
        req = new_sess(jwt=True).request(method, url, json=js, timeout=60)
        if retry and req.status_code == 401:
            get_inst_acc_tok(cached=False)
            retry = False
        else:
            req.raise_for_status()
            return req.json()


def get_api(url: str):
    return send_api('GET', url)


def post_api(url: str, js: 'dict[str, object]'):
    return send_api('POST', url, js)


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
    q = f'{title[:256]} in:title is:open is:issue repo:{OWNER}/{REPO}'
    return get_api(
        f'https://api.github.com/search/issues?q={quote_plus(q)}&per_page=100'
        # TODO &page=1 ...
    )


def create_comment(issue_id: int, body: 'str'):
    return post_api(
        f'https://api.github.com/repos/{OWNER}/{REPO}/issues/{issue_id}/comments',
        {'body': body})


@dataclass
class Issue:
    rowid: int
    title: str
    _body: 'str|None'
    milestone: 'str|None'
    labels: 'list[str]|None'
    assignees: 'list[str]|None'
    unix_epoch: int

    def body(self) -> str:
        body = self._body if self._body else ''

        dt = datetime.utcfromtimestamp(self.unix_epoch).replace(tzinfo=utc)
        loc = getlocale(LC_TIME)
        body += (
            '\n\n'
            '--------------\n'
            'Time happened:\n```\n'
            f'UTC:           {dt.isoformat()}\n'
            f'US/Eastern:    {dt.astimezone(timezone("US/Eastern")).isoformat()}, {setlocale(LC_TIME, "en_US") and dt.astimezone(timezone("US/Eastern")).strftime(r"%a %p %I:%M:%S.%f")}\n'
            f'Asia/Shanghai: {dt.astimezone(timezone("Asia/Shanghai")).isoformat()}, {setlocale(LC_TIME, "zh_CN") and dt.astimezone(timezone("Asia/Shanghai")).strftime(r"%a %p %I:%M:%S.%f")}\n'
            '```\n')
        setlocale(LC_TIME, loc)
        return body


if __name__ == '__main__':
    self_check()

    for issue_ in get_db().execute(
            'select title,body,milestone,labels,assignees,rowid,unix_epoch '
            f'from {ISSUES_TABLE_NAME} where {ISSUES_SUB_ROW_NAME}!=1'
    ).fetchall():
        issue = Issue(
            title=issue_[0],
            _body=issue_[1],
            milestone=issue_[2],
            labels=[x.strip() for x in t.cast(str, issue_[3]).split(';')]
            if issue_[3] else None,
            assignees=[x.strip() for x in t.cast(str, issue_[4]).split(';')]
            if issue_[4] else None,
            rowid=issue_[5],
            unix_epoch=issue_[6])

        for search in t.cast('list[dict[str, object]]',
                             search_open_issue(issue.title)['items']):
            if search['title'] == issue.title:
                create_comment(t.cast(int, search['id']), issue.body())
                break
        else:
            create_issue(issue.title, issue.body(), issue.milestone,
                         issue.labels, issue.assignees)
