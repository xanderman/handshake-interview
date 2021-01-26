#!/usr/bin/python3

import app
import unittest

class TestApp(Chirps):
    def GET_a(self):
        pass

class HandshakeAppTest(unittest.TestCase):
    def test_GET_a(self):
        app = mock(TestApp())
        app.url = "/a"
        app.do_GET()
        app.verify("GET_a")

    def test_GET_notAMethod(self):
        app = mock(TestApp())
        app.url = "/garbage"
        app.do_GET()
        app.verify("send_response", 404)

