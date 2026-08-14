"""python -m bro"""

from __future__ import annotations


def main() -> None:
    from bro.apps.desktop.main import main as desktop_main

    desktop_main()


if __name__ == "__main__":
    main()
