"""Entry point for ``python -m macsrv``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())