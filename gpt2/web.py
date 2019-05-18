#!/usr/bin/env python
import gpt_2_simple as gpt2
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote_plus
import threading


class Gpt(object):
    def __init__(self):
        self.sess = gpt2.start_tf_sess()
        gpt2.load_gpt2(self.sess)
        self.lock = threading.Lock()

    def generate(self, start="prompt: So, what's new around here?"):
        with self.lock:
            single_text = gpt2.generate(
                self.sess,
                length=250,
                temperature=0.75,
                top_k=0,
                return_as_list=True,
                temperature=0.75,
                include_prefix=False,
                truncate="<|endoftext|>",
                prefix=start
                )[0]
        return single_text


class Web(BaseHTTPRequestHandler):
    def do_GET(self):
        global gpt
        if not self.path.startswith("/asr33bot/"):
            self.send_response(404)
            self.end_headers()
            return
        prompt = unquote_plus(self.path[10:])
        print(prompt)
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        resp = gpt.generate(prompt)
        print(resp)
        self.wfile.write(resp.encode("utf-8"))


def run(server_class=HTTPServer, handler_class=Web, port=5599):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print("Running")
    httpd.serve_forever()


gpt = Gpt()


if __name__ == "__main__":
    run()
