"""CLI entrypoint shim

This lightweight module exposes start_server() and run() so the monolith script
can call into the modular package. Keep this file minimal — most logic belongs
in other modules.
"""
from . import config, core, burners, assets


def start_server(host: str = None, port: int = None):
    host = host or config.WEB_HOST
    port = port or config.WEB_PORT
    print(f"[flowstation.cli] start_server host={host} port={port}")
    # TODO: delegate to web/ws modules (not implemented here)


def run_from_args(argv=None):
    """Simple run wrapper called from FlowStation-v1.1.0-FC_FLOW.py shim."""
    # parse args minimally
    import argparse
    parser = argparse.ArgumentParser(prog="flowstation")
    parser.add_argument("--host", default=config.WEB_HOST)
    parser.add_argument("--port", type=int, default=config.WEB_PORT)
    args = parser.parse_args(argv)
    start_server(args.host, args.port)


def main():
    run_from_args()

