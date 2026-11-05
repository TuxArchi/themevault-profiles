# Perfiles de ThemeVault

Configuraciones de escritorio que la app muestra en su sección **Comunidad**.

Un perfil **no es una copia**: es la descripción del aspecto —tema, iconos,
cursores, esquema de color y ajustes— sin archivos de tema, sin rutas y sin
datos personales. Los temas se instalan aparte (paquete de la distro o tienda).

Escritorios admitidos: `kde`, `gnome`, `xfce`, `hyprland`, `niri`, `sway`,
`river`, `wayfire`, `labwc`, `cinnamon`, `mate`, `budgie`, `lxqt` y `other`.

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

- **Solo configuración + portada.** Nada de binarios, scripts ni archivos de
  tema.
- **Sin datos personales**: ni rutas (`/home/...`, `~`), ni historial, ni
  nombres de archivos del escritorio, ni capturas que muestren tu fondo.
  El validador los rechaza.
- **Autor = tu usuario de GitHub.** El `author` tiene que coincidir con la
  cuenta que abre el pull request; el CI lo verifica. Un perfil no se puede
  publicar ni editar a nombre de otra persona. Si un id ya existe, pertenece a
  quien lo publicó primero. Los maintainers de `MAINTAINERS` pueden hacer
  importaciones y el PR queda registrado.
- **Licencia declarada** de esta lista: `CC0-1.0`, `CC-BY-4.0`,
  `CC-BY-SA-4.0`, `MIT`, `GPL-3.0-or-later`.
- **Nombre de tema en `requires`**, no el archivo: quien lo aplique lo instala
  por su cuenta.
- **Compositores Wayland**: un perfil puede declarar `hyprland`, `niri`,
  `sway`, `river`, `wayfire` o `labwc`, y usar `requires` para iconos, cursor
  o GTK. Los atajos, comandos y archivos de configuración del compositor
  **no** se publican; nunca se incluyen en `profile.json`.

## Estructura

```
index.json                     ← generado, no editar a mano
profiles/<id>/profile.json
profiles/<id>/cover.png        ← opcional, PNG < 1.5 MB
```

El índice guarda el `sha256` de cada `profile.json`: la app lo verifica al
descargar.

## Privacidad

El detalle completo está en el repositorio principal:
[docs/PRIVACY.md](https://github.com/TuxArchi/themevault/blob/main/docs/PRIVACY.md).

Para pedir la baja de un perfil, abrí un issue o un PR eliminando su carpeta y
regenerando el índice.
