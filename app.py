#!/usr/bin/python3

import sqlite3
import json
import time

from collections import namedtuple
from http.client import HTTPSConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
from urllib.parse import unquote_plus
from urllib.parse import urlparse

Chirp = namedtuple('Chirp', 'id, text, votes')
DATABASE = 'chirps.db'

class Chirps(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        action = url.path.split('/')[1]
        handler = getattr(self, f'GET_{action}', None)
        if handler is None:
            self.send_response(404)
            self.end_headers()
            return
        handler()

    def do_POST(self):
        url = urlparse(self.path)
        action = url.path.split('/')[1]
        handler = getattr(self, f'POST_{action}', None)
        if handler is None:
            self.send_response(404)
            self.end_headers()
            return
        handler()

    def GET_index(self):
        html = ['<html><head><title>Chirps Index</title></head>']
        html.append('<body><ul>')

        html.append("<h1>What's on your mind?</h1>")
        html.append('<form action="/addChirp" method="post">')
        html.append('<input type="text" name="text" required>')
        html.append('<input type="submit" value="Submit">')
        html.append('</form>')

        html.append('<h1>CHIRPS</h1>')
        html.append('<ul>')
        for chirp in self.get_chirps():
            html.append('<li>')
            html.append(f'{chirp.id} -- {chirp.text.upper()}<br>')
            html.append(f'Upvotes: {chirp.votes}')
            html.append('<form action="/upvote" method="post">')
            html.append(f'<input type="hidden" name="id" value={chirp.id}>')
            html.append('<input type="submit" value="Upvote">')
            html.append('</form>')
            html.append('<form action="/downvote" method="post">')
            html.append(f'<input type="hidden" name="id" value={chirp.id}>')
            html.append('<input type="submit" value="Downvote">')
            html.append('</form>')
            html.append('</li>')
        html.append('</ul>')

        html.append('</body></html>')

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes(''.join(html), 'utf-8'))

    def get_chirps(self):
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = lambda cursor, row: Chirp(*row)
        cur = conn.cursor()
        cur.execute('SELECT * FROM chirps ORDER BY id DESC')
        return cur.fetchall()

    def POST_addChirp(self):
        length = int(self.headers['Content-Length'])
        params = parse_qs(unquote_plus(self.rfile.read(length).decode('utf-8')))
        text = params['text'][0]
        chirp_id = self.write_chirp(text)

        self.send_response(303)
        self.send_header('Location', '/index')
        self.end_headers()
        self.send_push_request(chirp_id)

    def write_chirp(self, text):
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute('INSERT INTO chirps(text) VALUES(?)', (text,))
        conn.commit()
        return cur.lastrowid

    def POST_upvote(self):
        length = int(self.headers['Content-Length'])
        params = parse_qs(unquote_plus(self.rfile.read(length).decode('utf-8')))
        chirp_id = params['id'][0]
        self.upvote(chirp_id)

        self.send_response(303)
        self.send_header('Location', '/index')
        self.end_headers()
        self.send_push_request(chirp_id)

    def upvote(self, chirp_id):
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = lambda cursor, row: Chirp(*row)
        cur = conn.cursor()
        cur.execute('SELECT * FROM chirps WHERE id = ?', (chirp_id,))
        chirp = cur.fetchall()[0]
        cur.execute('UPDATE chirps SET votes = ? WHERE id = ?', (chirp.votes + 1, chirp.id))
        conn.commit()

    def POST_downvote(self):
        length = int(self.headers['Content-Length'])
        params = parse_qs(unquote_plus(self.rfile.read(length).decode('utf-8')))
        chirp_id = params['id'][0]
        downvoted = self.downvote(chirp_id)

        self.send_response(303)
        self.send_header('Location', '/index')
        self.end_headers()
        if downvoted:
            self.send_push_request(chirp_id)

    def downvote(self, chirp_id):
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = lambda cursor, row: Chirp(*row)
        cur = conn.cursor()
        cur.execute('SELECT * FROM chirps WHERE id = ?', (chirp_id,))
        chirp = cur.fetchall()[0]
        votes = chirp.votes
        if votes == 0:
            return False
        cur.execute('UPDATE chirps SET votes = ? WHERE id = ?', (votes - 1, chirp.id))
        conn.commit()
        return True

    def send_push_request(self, chirp_id):
        service = HTTPSConnection('bellbird.joinhandshake-internal.com')
        service.request(
                "POST",
                "/push",
                body=json.dumps({'chirp_id': chirp_id}))
        response = service.getresponse()
        print(f'Response for chirp {chirp_id}: {response.status}')

if __name__ == '__main__':
  try:
    with ThreadingHTTPServer(('', 8080), Chirps) as server:
      print('Server started at http://localhost:8080')
      server.serve_forever()
  except KeyboardInterrupt:
    pass
  print('Server stopped.')
