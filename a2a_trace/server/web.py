"""
A2A Trace Server — Real-time agent topology visualization.

Serves a web dashboard that shows:
- Agent network topology (real-time)
- Trace timeline
- Span details
"""

from __future__ import annotations

import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
from typing import Optional

from ..collector import get_collector


class A2ATraceHandler(SimpleHTTPRequestHandler):
    """HTTP handler for A2A trace visualization server."""
    
    TEMPLATE_DIR = Path(__file__).parent / "templates"
    STATIC_DIR = Path(__file__).parent / "static"
    
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_template("index.html")
        elif self.path == "/api/topology":
            self._serve_topology()
        elif self.path.startswith("/api/traces"):
            self._serve_traces()
        elif self.path.startswith("/api/trace/"):
            trace_id = self.path.split("/api/trace/")[1]
            self._serve_trace(trace_id)
        elif self.path.startswith("/static/"):
            self._serve_static(self.path[8:])
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
    
    def _serve_template(self, name: str):
        """Serve an HTML template."""
        path = self.TEMPLATE_DIR / name
        if not path.exists():
            self.send_error(404)
            return
        
        content = path.read_text()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode())
    
    def _serve_static(self, path: str):
        """Serve static files (CSS, JS)."""
        full_path = self.STATIC_DIR / path
        if not full_path.exists():
            self.send_error(404)
            return
        
        content = full_path.read_bytes()
        content_type = "text/css" if path.endswith(".css") else "application/javascript"
        
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(content)
    
    def _serve_topology(self):
        """Serve topology data as JSON."""
        collector = get_collector()
        topology = collector.get_topology(since_minutes=30)
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(topology, indent=2).encode())
    
    def _serve_traces(self):
        """Serve recent traces."""
        collector = get_collector()
        traces = collector.get_recent_traces(limit=20)
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(traces, indent=2).encode())
    
    def _serve_trace(self, trace_id: str):
        """Serve detailed trace data."""
        collector = get_collector()
        spans = collector.get_trace(trace_id)
        
        from dataclasses import asdict
        spans_data = [asdict(s) for s in spans]
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(spans_data, indent=2).encode())
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def run_server(
    host: str = "localhost",
    port: int = 8081,
    debug: bool = False,
):
    """Run the A2A trace visualization server."""
    server = HTTPServer((host, port), A2ATraceHandler)
    print(f"🔍 A2A Trace Dashboard: http://{host}:{port}")
    server.serve_forever()


def run_server_background(host: str = "localhost", port: int = 8081):
    """Run the server in a background thread."""
    thread = Thread(target=run_server, args=(host, port), daemon=True)
    thread.start()
    return thread
