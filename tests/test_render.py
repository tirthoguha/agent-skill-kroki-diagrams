"""Local HTTP integration tests; no Docker or external network needed."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET
import zlib

HELPER = Path(__file__).resolve().parents[1] / 'skills/kroki/scripts/render.py'
VALID_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-2 -3 20 30"><text x="0" y="10">Sample</text></svg>'

def chunk(kind, data):
    return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
PNG = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff')) + chunk(b'IEND', b'')

class RenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'folder with spaces'
        self.root.mkdir()
        self.source = self.root / 'sample.mmd'
        self.source.write_text('flowchart TB\nA --> B\n')
        self.status, self.svg, self.png = 200, VALID_SVG, PNG
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.received = self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(owner.status); self.end_headers()
                self.wfile.write(owner.png if '/png' in self.path else owner.svg)
            def log_message(self, *args):
                pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.temp.cleanup()
    def render(self, fmt='svg'):
        env = dict(os.environ, KROKI_PORT=str(self.server.server_port))
        return subprocess.run([sys.executable, str(HELPER), str(self.source), '--format', fmt], env=env, text=True, capture_output=True)
    def test_svg_uses_env_port_and_preserves_vector_text(self):
        result = self.render(); self.assertEqual(result.returncode, 0, result.stderr)
        root = ET.parse(self.source.with_suffix('.svg')).getroot()
        self.assertEqual(root.get('viewBox'), '-2 -3 20 30')
        self.assertEqual(root[0].get('x'), '-2.0')
        self.assertEqual(root[0].get('style'), 'fill:#ffffff;stroke:none')
        self.assertEqual(root[-1].text, 'Sample')
        self.assertEqual(self.received, self.source.read_bytes())
    def test_explicit_out_dir_overrides_source_directory(self):
        destination = self.root / 'requested output'
        env = dict(os.environ, KROKI_PORT=str(self.server.server_port))
        result = subprocess.run([sys.executable, str(HELPER), str(self.source),
                                 '--format', 'svg', '--out-dir', str(destination)],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((destination / 'sample.svg').is_file())
        self.assertFalse(self.source.with_suffix('.svg').exists())

    def test_http_failure_preserves_previous_output(self):
        self.status = 500
        target = self.source.with_suffix('.svg'); target.write_bytes(b'previous good export')
        self.assertNotEqual(self.render().returncode, 0)
        self.assertEqual(target.read_bytes(), b'previous good export')
        self.assertFalse(list(self.root.glob('.kroki-*')))
    def test_non_svg_response_is_not_delivered(self):
        self.svg = b'<html>Not a diagram</html>'
        self.assertNotEqual(self.render().returncode, 0)
        self.assertFalse(self.source.with_suffix('.svg').exists())
    def test_second_format_failure_preserves_both_outputs(self):
        self.svg = b'<svg'  # PNG succeeds; SVG validation fails.
        for ext in ['png', 'svg']:
            self.source.with_suffix('.'+ext).write_bytes(('old '+ext).encode())
        result = self.render('both')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('PNG needs', result.stderr, 'Install a flattener to exercise this test')
        for ext in ['png', 'svg']:
            self.assertEqual(self.source.with_suffix('.'+ext).read_bytes(), ('old '+ext).encode())
        self.assertFalse(list(self.root.glob('.kroki-*')))

if __name__ == '__main__':
    unittest.main()
