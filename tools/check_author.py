#!/usr/bin/env python3
"""Verifica que quien abre el PR sea el autor del perfil.

Reglas:
  · Un perfil solo lo puede publicar o editar su propio autor.
  · Un id existente no se puede apropiar ni transferir desde otra cuenta.
  · Quien figura en MAINTAINERS puede publicar/importar en nombre de otro.

Uso (CI):
    python tools/check_author.py --author "$PR_AUTHOR" --base origin/main

En CI conviene ejecutar la copia de la rama base (`git show origin/main:tools/...`)
para que un PR no pueda modificar el validador ni MAINTAINERS y auto-habilitarse.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "profiles"


def _run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)


def changed_ids(base: str) -> set[str]:
    """Ids tocados por el PR (altas, bajas y renombres)."""
    proc = _run(["git", "diff", "--name-status", f"{base}...HEAD", "--", "profiles"])
    if proc.returncode != 0:
        raise SystemExit(f"no se pudo comparar con {base}: {proc.stderr.strip()}")

    ids: set[str] = set()
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, paths = parts[0], parts[1:]
        for path in paths:
            pieces = Path(path).parts
            if len(pieces) >= 2 and pieces[0] == "profiles":
                ids.add(pieces[1])
    return ids


def author_in(ref: str, profile_id: str) -> str:
    proc = _run(["git", "show", f"{ref}:profiles/{profile_id}/profile.json"])
    if proc.returncode != 0:
        return ""
    try:
        return str(json.loads(proc.stdout).get("author", ""))
    except ValueError:
        return ""


def local_author(profile_id: str) -> str:
    path = PROFILES / profile_id / "profile.json"
    if not path.is_file():
        return ""
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get("author", ""))
    except (OSError, ValueError):
        return ""


def maintainers(base: str) -> set[str]:
    """Lista de maintainers de la rama base (nunca la del PR)."""
    proc = _run(["git", "show", f"{base}:MAINTAINERS"])
    if proc.returncode != 0:
        return set()
    out = set()
    for line in proc.stdout.splitlines():
        text = line.strip()
        if text and not text.startswith("#"):
            out.add(text.lower())
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author", required=True, help="usuario que abrió el PR")
    parser.add_argument("--base", default="origin/main", help="rama base del PR")
    parser.add_argument("--root", help="raíz del repositorio (por defecto, la del script)")
    args = parser.parse_args(argv)

    global ROOT, PROFILES
    if args.root:
        ROOT = Path(args.root).resolve()
        PROFILES = ROOT / "profiles"

    author = args.author.strip()
    if not author:
        print("Falta el usuario del PR.")
        return 1

    ids = changed_ids(args.base)
    if not ids:
        print("Sin perfiles modificados: nada que verificar.")
        return 0

    if author.lower() in maintainers(args.base):
        print(f"Override de maintainer @{author}: se permite publicar en nombre de otro.")
        return 0

    problems: list[str] = []
    for profile_id in sorted(ids):
        new = local_author(profile_id)
        old = author_in(args.base, profile_id)

        if new and new.lower() != author.lower():
            problems.append(
                f"{profile_id}: el perfil dice @{new}, pero el PR lo abre @{author}"
            )
        if old and old.lower() != author.lower():
            problems.append(
                f"{profile_id}: ya pertenece a @{old}; no se puede editar desde @{author}"
            )

    if problems:
        print("Autoría inválida:")
        for problem in problems:
            print(f"  · {problem}")
        print("\nSi sos maintainer, agregá tu usuario a MAINTAINERS o abrí el PR con la cuenta dueña.")
        return 1

    print(f"Autoría OK: @{author} sobre {len(ids)} perfil(es).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
