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
import shutil
import subprocess
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
    "i3",
    "openbox",
    "cosmic",
    "other",
}
LICENSES = {"CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "MIT", "GPL-3.0-or-later"}
REQUIRES = {"plasma_style", "color_scheme", "icons", "cursor", "gtk", "packages"}
BACKENDS = {"ini", "dconf", "xfconf"}
UNSAFE = re.compile(r"(^[/~])|(file:)|(\.\./)|([A-Za-z]:\\\\)")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
HANDLE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")

ALLOWED_FILES = {
    "profile.json",
    "cover.png",
    "cover.jpg",
    "wallpaper.jpg",
    "wallpaper.jpeg",
    "wallpaper.png",
    "wallpaper.webp",
    "wallpaper.mp4",
    "plugins",
    "assets",
}
MAX_PROFILE = 256 * 1024
MAX_COVER = 3 * 1024 * 1024
MAX_WALLPAPER = 60 * 1024 * 1024
MAX_PLUGIN = 25 * 1024 * 1024
SHA = re.compile(r"^[0-9a-f]{64}$")
SECRET = re.compile(
    r"(?i)(token|password|passwd|secret|api[_-]?key|authorization|bearer|"
    r"ssh-|id_rsa|id_ed25519|\.ssh|\.env|file://|https?://|@[^ ]+\.[^ ]+)"
)


def safe(value: str) -> bool:
    text = str(value).strip()
    return bool(text) and len(text) <= 200 and not UNSAFE.search(text)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _probe_video(path: Path) -> tuple[dict | None, str]:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return None, "ffprobe no disponible"
    try:
        proc = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, "ffprobe fallo"
    if proc.returncode != 0:
        return None, "ffprobe rechazo el video"
    try:
        return json.loads(proc.stdout.decode("utf-8", "replace")), ""
    except ValueError:
        return None, "ffprobe devolvio JSON invalido"


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
        if cover not in ("cover.png", "cover.jpg") or not file.is_file():
            problems.append(f"{folder.name}: portada invalida")
        elif file.stat().st_size > MAX_COVER:
            problems.append(f"{folder.name}: portada demasiado grande")
        elif cover == "cover.png" and file.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
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

    if data.get("name") and not safe(str(data["name"])):
        problems.append(f"{folder.name}: nombre con ruta o dato sospechoso")
    if data.get("description") and (
        not safe(str(data["description"])) or SECRET.search(str(data["description"]))
    ):
        problems.append(f"{folder.name}: descripcion con dato sospechoso")

    wallpaper = data.get("wallpaper") or {}
    if wallpaper:
        kind = wallpaper.get("kind")
        if kind not in ("image", "video"):
            problems.append(f"{folder.name}: wallpaper kind invalido")
        if not SHA.fullmatch(str(wallpaper.get("sha256", ""))):
            problems.append(f"{folder.name}: wallpaper sin sha256 valido")
        for key in ("file", "fallback"):
            name = str(wallpaper.get(key, "") or "")
            if not name:
                continue
            file = folder / name
            if Path(name).is_absolute() or ".." in Path(name).parts:
                problems.append(f"{folder.name}: wallpaper ruta invalida {name}")
            elif not file.is_file():
                problems.append(f"{folder.name}: falta wallpaper {name}")
            elif file.stat().st_size > MAX_WALLPAPER:
                problems.append(f"{folder.name}: wallpaper demasiado grande")
            elif key == "file" and _sha(file) != str(wallpaper.get("sha256", "")):
                problems.append(f"{folder.name}: wallpaper no coincide con el sha256")
        try:
            if float(wallpaper.get("duration") or 0) > 600:
                problems.append(f"{folder.name}: video demasiado largo")
            if int(wallpaper.get("size") or 0) > MAX_WALLPAPER:
                problems.append(f"{folder.name}: video demasiado grande")
        except (TypeError, ValueError):
            problems.append(f"{folder.name}: metadatos de wallpaper invalidos")

        if kind == "video":
            name = str(wallpaper.get("file", "") or "")
            file = folder / name
            if name and file.is_file():
                probe, reason = _probe_video(file)
                if probe is None:
                    if reason != "ffprobe no disponible":
                        problems.append(f"{folder.name}: no se pudo validar el video ({reason})")
                else:
                    streams = probe.get("streams") or []
                    video = next(
                        (s for s in streams if s.get("codec_type") == "video"), None
                    )
                    if video is None:
                        problems.append(f"{folder.name}: el wallpaper no tiene video")
                    elif str(video.get("codec_name")) != "h264":
                        problems.append(f"{folder.name}: el video debe ser H.264")
                    if any(s.get("codec_type") == "audio" for s in streams):
                        problems.append(f"{folder.name}: el video no debe tener audio")
                    try:
                        duration = float(
                            video.get("duration")
                            or (probe.get("format") or {}).get("duration")
                            or 0
                        )
                        if duration > 600:
                            problems.append(f"{folder.name}: el video supera 10 minutos")
                    except (TypeError, ValueError):
                        pass

    for plugin in data.get("plugins") or []:
        name = str(plugin.get("file", "") or "")
        target = str(plugin.get("target", "") or "")
        file = folder / name
        if not name or Path(name).is_absolute() or ".." in Path(name).parts:
            problems.append(f"{folder.name}: plugin ruta invalida")
        elif Path(name).parts[0] != "plugins":
            problems.append(f"{folder.name}: plugin fuera de plugins/")
        elif not name.endswith((".tar.gz", ".zip")):
            problems.append(f"{folder.name}: formato de plugin no permitido")
        elif not target.startswith("~/"):
            problems.append(f"{folder.name}: plugin destino fuera del home")
        elif not SHA.fullmatch(str(plugin.get("sha256", ""))):
            problems.append(f"{folder.name}: plugin sin sha256")
        elif not file.is_file():
            problems.append(f"{folder.name}: falta plugin {name}")
        elif file.stat().st_size > MAX_PLUGIN:
            problems.append(f"{folder.name}: plugin demasiado grande")
        elif _sha(file) != str(plugin.get("sha256", "")):
            problems.append(f"{folder.name}: plugin no coincide con el sha256")

    for asset in data.get("assets") or []:
        name = str(asset.get("file", "") or "")
        url = str(asset.get("url", "") or "")
        if name:
            file = folder / name
            if Path(name).parts[0] != "assets" or Path(name).is_absolute() or ".." in Path(name).parts:
                problems.append(f"{folder.name}: asset ruta invalida")
            elif not name.endswith((".tar.gz", ".zip")):
                problems.append(f"{folder.name}: asset formato no permitido")
            elif not str(asset.get("target", "")).startswith("~/"):
                problems.append(f"{folder.name}: asset destino fuera del home")
            elif not file.is_file():
                problems.append(f"{folder.name}: falta asset {name}")
            elif file.stat().st_size > MAX_PLUGIN:
                problems.append(f"{folder.name}: asset demasiado grande")
            elif _sha(file) != str(asset.get("sha256", "")):
                problems.append(f"{folder.name}: asset no coincide con el sha256")
        if url and not (
            url.startswith("https://github.com/")
            or url.startswith("https://raw.githubusercontent.com/")
            or url.startswith("https://objects.githubusercontent.com/")
            or url.startswith("https://codeload.github.com/")
        ):
            problems.append(f"{folder.name}: asset con URL no permitida")
        if not name and not url:
            problems.append(f"{folder.name}: asset sin archivo ni URL")
        if not SHA.fullmatch(str(asset.get("sha256", ""))):
            problems.append(f"{folder.name}: asset sin sha256")

    for entry in data.get("keybinds") or []:
        text = " ".join(str(entry.get(key, "")) for key in ("arg", "description", "dispatcher"))
        if entry.get("script") or UNSAFE.search(text) or SECRET.search(text):
            problems.append(f"{folder.name}: atajo con ruta o secreto")

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
        entry = {
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
        if data.get("wallpaper"):
            entry["wallpaper"] = data["wallpaper"]
        if data.get("plugins"):
            entry["plugins"] = len(data["plugins"])
        if data.get("assets"):
            entry["assets"] = len(data["assets"])
        if data.get("keybinds"):
            entry["keybinds"] = len(data["keybinds"])
        entries.append(entry)
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
