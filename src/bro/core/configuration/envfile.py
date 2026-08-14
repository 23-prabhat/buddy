from __future__ import annotations

from pathlib import Path


def project_env_path() -> Path:
    """
    Resolve repo-root .env when running from a source checkout.
    Layout: <repo>/src/bro/core/configuration/envfile.py
    parents: 0=configuration 1=core 2=bro 3=src 4=repo
    Falls back to CWD .env for installed packages.
    """
    here = Path(__file__).resolve()
    candidates = [
        here.parents[4] / ".env",  # src layout checkout
        here.parents[3] / ".env",  # alternate
        Path.cwd() / ".env",
        Path.home() / ".config" / "bro" / ".env",
    ]
    for p in candidates:
        if p.is_file():
            return p
    # Prefer repo root when developing
    if (here.parents[4] / "pyproject.toml").is_file():
        return here.parents[4] / ".env"
    return Path.cwd() / ".env"


def upsert_env_values(updates: dict[str, str], path: Path | None = None) -> Path:
    """Create/update keys in .env without dropping unrelated lines."""
    env_path = path or project_env_path()
    existing: dict[str, str] = {}
    order: list[str] = []

    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            existing[key] = val
            if key not in order:
                order.append(key)

    for k, v in updates.items():
        existing[k] = v
        if k not in order:
            order.append(k)

    env_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Managed by bro — do not commit secrets"]
    for k in order:
        lines.append(f"{k}={existing[k]}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path
