"""Console entry point for the scribe-visualizer Streamlit app.

Launches `streamlit run` on the bundled app.py. Any additional command-line
arguments are forwarded to streamlit (e.g. `scribe-visualizer --server.port 8502`).
"""

import sys
from pathlib import Path


def main() -> None:
    try:
        from streamlit.web import cli as stcli
    except ImportError as exc:
        raise SystemExit(
            "The Streamlit visualizer requires the 'visualizer' extra.\n"
            "Install it with:\n"
            "    pip install 'scribe-eval[visualizer]'"
        ) from exc

    app_path = Path(__file__).parent / "app.py"
    sys.argv = ["streamlit", "run", str(app_path), *sys.argv[1:]]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
