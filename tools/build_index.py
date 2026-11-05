#!/usr/bin/env python3
"""Valida los perfiles del repositorio. Sin dependencias externas.

Uso:
    python tools/build_index.py            # reescribe index.json
    python tools/build_index.py --check    # falla si index.json no esta al dia
    python tools/build_index.py --root DIR # valida otro checkout (CI con el script de la base)
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "profiles"
INDEX = ROOT / "index.json"

SCHEMA = 1
DESKTOPS = {
    "kde",
    "gnome",
    "xfce",
    "hyprland",
    "niri",
    "sway",
    "river",
    "wayfire",
    "labwc",
    "cinnamon",
    "mate",
    "budgie",
    "lxqt",
    "other",
}
LICENSES = {"CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "MIT", "GPL-3.0-or-later"}
REQUIRES = {"plasma_style", "color_scheme", "icons", "cursor", "gtk", "packages"}
BACKENDS = {"ini", "dconf", "xfconf"}
UNSAFE = re.compile(r"(^[/~])|(file:)|(\.\./)|([A-Za-z]:\\\\)")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
HANDLE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")

ALLOWED_FILES = {"profile.json", "cover.png"}
MAX_PROFILE = 64 * 1024
MAX_COVER = 1536 * 1024


def safe(value: str) -> bool:
    text = str(value).strip()
    return bool(text) and len(text) <= 200 and not UNSAFE.search(text)


def validate(folder: Path) -> tuple[dict | None, list[str]]:
    problems: list[str] = []
    path = folder / "profile.json"
    if not path.is_file():
        return None, [f"{folder.name}: falta profile.json"]
    if path.stat().st_size > MAX_PROFILE:
        return None, [f"{folder.name}: profile.json demasiado grande"]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return None, [f"{folder.name}: JSON invalido ({exc})"]

    extra = {p.name for p in folder.iterdir()} - ALLOWED_FILES
    if extra:
        problems.append(f"{folder.name}: archivos no permitidos: {', '.join(sorted(extra))}")

    if data.get("schema") != SCHEMA:
        problems.append(f"{folder.name}: schema distinto de {SCHEMA}")
    if data.get("id") != folder.name:
        problems.append(f"{folder.name}: el id no coincide con la carpeta")
    if not SLUG.fullmatch(str(data.get("id", ""))):
        problems.append(f"{folder.name}: id invalido")
    if not str(data.get("name", "")).strip():
        problems.append(f"{folder.name}: falta name")
    if not str(data.get("author", "")).strip():
        problems.append(f"{folder.name}: falta author")
    elif not HANDLE.fullmatch(str(data.get("author", "")).strip()):
        problems.append(f"{folder.name}: author debe ser un usuario de GitHub (sin @)")
    if data.get("license") not in LICENSES:
        problems.append(f"{folder.name}: licencia no permitida")
    if data.get("desktop") not in DESKTOPS:
        problems.append(f"{folder.name}: escritorio desconocido")

    preview = data.get("preview") or {}
    cover = str(preview.get("cover") or "")
    if cover:
        file = folder / cover
        if cover != "cover.png" or not file.is_file():
            problems.append(f"{folder.name}: portada invalida")
        elif file.stat().st_size > MAX_COVER:
            problems.append(f"{folder.name}: portada demasiado grande")
        elif file.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            problems.append(f"{folder.name}: la portada no es PNG")

    for color in preview.get("palette") or []:
        if not HEX.fullmatch(str(color)):
            problems.append(f"{folder.name}: color invalido {color}")

    for key in (data.get("requires") or {}):
        if key not in REQUIRES:
            problems.append(f"{folder.name}: campo desconocido en requires: {key}")

    settings = data.get("settings") or []
    if len(settings) > 80:
        problems.append(f"{folder.name}: demasiados ajustes")
    for setting in settings:
        backend = setting.get("backend")
        if backend not in BACKENDS:
            problems.append(f"{folder.name}: backend desconocido {backend}")
            continue
        if not safe(str(setting.get("value", ""))):
            problems.append(f"{folder.name}: valor sospechoso en {setting.get('key', setting.get('prop', '?'))}")
        if backend == "ini" and not (setting.get("file") and setting.get("group") and setting.get("key")):
            problems.append(f"{folder.name}: ajuste ini incompleto")
        if backend == "dconf" and not (str(setting.get("path", "")).startswith("/") and setting.get("key")):
            problems.append(f"{folder.name}: ajuste dconf incompleto")
        if backend == "xfconf" and not (setting.get("channel") and setting.get("prop")):
            problems.append(f"{folder.name}: ajuste xfconf incompleto")

    return data, problems


def build() -> tuple[dict, list[str]]:
    entries = []
    problems: list[str] = []
    for folder in sorted(p for p in PROFILES.iterdir() if p.is_dir()):
        data, issues = validate(folder)
        problems.extend(issues)
        if data is None:
            continue
        digest = hashlib.sha256((folder / "profile.json").read_bytes()).hexdigest()
        preview = data.get("preview") or {}
        entries.append(
            {
                "id": data["id"],
                "name": data["name"],
                "author": data["author"],
                "license": data["license"],
                "desktop": data["desktop"],
                "description": str(data.get("description", ""))[:200],
                "requires": data.get("requires") or {},
                "settings": len(data.get("settings") or []),
                "palette": preview.get("palette") or [],
                "cover": str(preview.get("cover") or ""),
                "sha256": digest,
            }
        )
    return {"schema": SCHEMA, "profiles": entries}, problems


def main(argv: list[str]) -> int:
    global ROOT, PROFILES, INDEX
    if "--root" in argv:
        pos = argv.index("--root")
        try:
            ROOT = Path(argv[pos + 1]).resolve()
        except IndexError:
            print("--root necesita una ruta")
            return 1
        PROFILES = ROOT / "profiles"
        INDEX = ROOT / "index.json"
        argv = argv[:pos] + argv[pos + 2:]

    index, problems = build()
    if problems:
        print("Perfiles con problemas:")
        for problem in problems:
            print("  ·", problem)
        return 1

    rendered = json.dumps(index, indent=2, ensure_ascii=False) + "\n"
    if "--check" in argv:
        current = INDEX.read_text(encoding="utf-8") if INDEX.is_file() else ""
        if current != rendered:
            print("index.json esta desactualizado: corre `python tools/build_index.py`")
            return 1
        print(f"OK: {len(index['profiles'])} perfiles validados")
        return 0

    INDEX.write_text(rendered, encoding="utf-8")
    print(f"index.json actualizado con {len(index['profiles'])} perfiles")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
