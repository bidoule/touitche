#!/opt/python3/bin/python3

import sys
import functools
import curses
import subprocess

import requests

class Kraken:
    ENDPOINT = 'https://api.twitch.tv/kraken'

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/vnd.twitchtv.v3+json'
        })

    def get(self, output, url, params=None):
        if params is None:
            params = {}
        j = self.session.get(self.ENDPOINT + url, params=params).json()
        yield from j[output]

    def get_list(self, output, url, params=None, limit=100):
        total = 1
        if params is None:
            params = {}
        params.update({
            'limit': limit,
            'offset': 0,
        })
        while params['offset'] < total:
            j = self.session.get(self.ENDPOINT + url, params=params).json()
            yield from j[output]
            params['offset'] += limit
            total = j['_total']

    def channels_followed(self, user):
        for follow in self.get_list('follows', '/users/%s/follows/channels' % user):
            yield follow['channel']

    def streams_followed(self, user):
        channels = ','.join(channel['name'] for channel in self.channels_followed(user))
        yield from self.get_list('streams', '/streams', params={'channel': channels})

    def live_streams(self, user):
        return [
            (stream['channel']['url'], "[%(game)s] %(display_name)s - %(status)s" % stream['channel'])
            for stream in self.streams_followed(user)
        ]


class Touitche:
    def __init__(self, user):
        self.k = Kraken()
        self.user = user
        self.choices = []
        self._select = 0
        self.refresh()

    def refresh(self):
        self.choices = self.k.live_streams(self.user)
        self._select = 0

    @property
    def select(self):
        return self._select

    @select.setter
    def select(self, value):
        self._select = value % len(self.choices)

    @property
    def choice(self):
        return self.choices[self.select][0]

    def main(self, stdscr):
        while True:
            stdscr.clear()
            for i, choice in enumerate(self.choices):
                style = curses.A_NORMAL
                if i == self.select:
                    style = curses.A_STANDOUT
                stdscr.addstr(i, 0, choice[1], style)
            stdscr.refresh()
            key = stdscr.getkey()
            if key == 'q':
                break
            elif key == 'KEY_UP':
                self.select -= 1
            elif key == 'KEY_DOWN':
                self.select += 1
            elif key == '\n':
                subprocess.call(['livestreamer', self.choice, 'best'])
                self.refresh()
            elif key == 'KEY_F(5)' or key == 'r':
                self.refresh()

if __name__ == '__main__':
    t = Touitche(sys.argv[1])
    curses.wrapper(t.main)
