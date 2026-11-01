# Perfiles de ThemeVault

Configuraciones de escritorio que la app muestra en su sección **Comunidad**.

Un perfil **no es una copia**: es la descripción del aspecto —tema, iconos,
cursores, esquema de color y ajustes— sin archivos de tema, sin rutas y sin
datos personales. Los temas se instalan aparte (paquete de la distro o tienda).

## Cómo publicar tu perfil

1. Exportalo desde la app o la terminal:

   ```bash
   themevault export-profile <tu-copia> \
       --name "Mi estilo" --author tu-usuario \
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
- **Licencia declarada** de esta lista: `CC0-1.0`, `CC-BY-4.0`,
  `CC-BY-SA-4.0`, `MIT`, `GPL-3.0-or-later`.
- **Nombre de tema en `requires`**, no el archivo: quien lo aplique lo instala
  por su cuenta.

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
