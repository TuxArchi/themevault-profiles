# Perfiles de ThemeVault

Configuraciones de escritorio que la app muestra en su sección **Comunidad**.

Un perfil es un **bundle aplicable**: fondo (imagen o video), apariencia,
layout de paneles/widgets, atajos seguros y plugins declarados. No incluye
historial, tokens, cuentas, capturas del escritorio, scripts personales ni
configuración interna de shells.

Escritorios admitidos: `kde`, `gnome`, `xfce`, `hyprland`, `niri`, `sway`,
`river`, `wayfire`, `labwc`, `cinnamon`, `mate`, `budgie`, `lxqt`, `i3`,
`openbox`, `cosmic` y `other`.

## Cómo publicar tu perfil

La forma más corta, con el repositorio clonado y `themevault` instalado:

```bash
themevault publish-profile ~/themevault-perfiles/mi-estilo --pr
```

Valida el perfil, lo copia a `profiles/<id>/`, regenera `index.json`, crea la
rama, la sube y abre el pull request (pide confirmación). Sin `--pr` deja el
commit local y muestra los comandos.

A mano:

1. Exportalo desde la app (botón **Compartir…** en el detalle de una copia) o
   desde la terminal:

   ```bash
   themevault export-profile <tu-copia> \
       --name "Mi estilo" --author tu-usuario-de-github \
       --license CC-BY-SA-4.0
   ```

2. Copiá la carpeta a `profiles/<id>/` (el `id` tiene que coincidir con el
   nombre de la carpeta: minúsculas, números y guiones).
3. Regenerá el índice:

   ```bash
   python tools/build_index.py
   ```

4. Abrí un pull request. CI valida el esquema, el índice y que no haya rutas ni
   archivos raros.

## Reglas

- **Solo personalización declarada.** Fondo, apariencia, layout, atajos seguros,
  plugins con hash/licencia y una portada generada desde el fondo.
- **Sin datos personales**: ni rutas (`/home/...`, `~`), ni historial, ni
  tokens, ni cuentas, ni capturas de ventanas, ni scripts personales, ni
  configuración interna de shells. El validador los rechaza.
- **Autor = tu usuario de GitHub.** El `author` tiene que coincidir con la
  cuenta que abre el pull request; el CI lo verifica. Un perfil no se puede
  publicar ni editar a nombre de otra persona. Si un id ya existe, pertenece a
  quien lo publicó primero. Los maintainers de `MAINTAINERS` pueden hacer
  importaciones y el PR queda registrado.
- **Licencia declarada** de esta lista: `CC0-1.0`, `CC-BY-4.0`,
  `CC-BY-SA-4.0`, `MIT`, `GPL-3.0-or-later`.
- **Nombre de tema en `requires`**, no el archivo: quien lo aplique lo instala
  por su cuenta.
- **Escritorios y compositores**: un perfil puede declarar `cinnamon`, `mate`,
  `budgie`, `lxqt`, `i3`, `openbox`, `cosmic`, `hyprland`, `niri`, `sway`,
  `river`, `wayfire` o `labwc`, y usar `requires` para iconos, cursor o GTK.
  Los atajos, comandos y archivos de configuración **no** se publican; nunca
  se incluyen en `profile.json`.

## Estructura

```
index.json                        ← generado, no editar a mano
profiles/<id>/profile.json
profiles/<id>/cover.jpg|png       ← opcional, < 3 MB
profiles/<id>/wallpaper.jpg|png   ← opcional
profiles/<id>/wallpaper.mp4       ← opcional, H.264 sin audio, <= 50 MB
profiles/<id>/plugins/*.tar.gz    ← opcional, <= 25 MB por plugin
profiles/<id>/assets/             ← referencias GitHub verificadas
```

Los videos se validan con `ffprobe`: H.264, sin audio, máximo 10 minutos y
50 MB. Los plugins deben traer `sha256`, licencia y un destino dentro de `~/`.
No se aceptan scripts de instalación ni rutas absolutas.

El índice guarda el `sha256` de cada `profile.json`: la app lo verifica al
descargar.

## Privacidad

El detalle completo está en el repositorio principal:
[docs/PRIVACY.md](https://github.com/TuxArchi/themevault/blob/main/docs/PRIVACY.md).

Para pedir la baja de un perfil, abrí un issue o un PR eliminando su carpeta y
regenerando el índice.
