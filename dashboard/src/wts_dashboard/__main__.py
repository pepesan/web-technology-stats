"""Arranque: `uv run wts-dashboard [--host H] [--port P] [--reload]`."""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Dashboard de web-technology-stats")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Recarga automática (desarrollo)")
    args = parser.parse_args()
    uvicorn.run(
        "wts_dashboard.app:create_app", factory=True, host=args.host, port=args.port, reload=args.reload
    )


if __name__ == "__main__":
    main()
