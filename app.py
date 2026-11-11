"""Run OpenFlow from source: python app.py."""
from openflow.app import main

if __name__ == "__main__":
    import sys
    if "--startup-test" in sys.argv:
        try:
            raise SystemExit(main())
        except Exception:
            import traceback
            from pathlib import Path
            Path("startup-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            raise SystemExit(1)
    raise SystemExit(main())
