# IconShift 🔄

**IconShift** es una suite de herramientas en Python diseñada para auditar, resolver y generar automáticamente iconos de aplicaciones en entornos de escritorio Linux, adaptándolos a temas monocromos o con paletas personalizadas (con soporte nativo para **ACYLS** u otros temas).

Sigue estrictamente la especificación **Freedesktop Icon Theme** (trazando la cadena transitiva de `Inherits=` desde `index.theme` hasta `hicolor`) y resuelve dinámicamente iconos que residen fuera de la jerarquía de temas estándar (como `/usr/share/pixmaps/` o paquetes en `/opt/`), sin ningún nombre de aplicación hardcodeado.

---

## Características Principales

- **Auditoría y Detección de Faltantes (`scan`):** Escanea los archivos `.desktop` del sistema y del usuario, determinando qué aplicaciones carecen de icono en el tema objetivo y localizando su archivo de respaldo exacto.
- **Salida Componible para Terminal:** Formateo en tabla para humanos, o delimitado (`tsv`, `csv`, `json`, `paths`, `icons`) listo para usar en tuberías con `cut`, `awk`, `grep`, `xargs` o `jq`.
- **Generación y Recoloreado Vectorial (`generate`):** Transforma iconos SVG preservando geometrías, opacidades y valores `none`/`transparent`. Soporta modo monocromo o bi-tono (luz y sombra).
- **Instalación Segura en Espacio de Usuario:** Por defecto, los iconos generados se guardan en `~/.local/share/icons/<theme>/scalable/apps/`, sin requerir permisos de `sudo` ni arriesgar sobreescrituras en `/usr/share/`.
- **Introspección de Paletas (`palette`):** Analiza y extrae las frecuencias de colores hexadecimales de cualquier tema instalado para auto-detectar su estética dominante.
- **Testing 100% Aislado:** Suite completa de pruebas con alta cobertura ejecutada exclusivamente en máquina virtual (`ulir-dev`) mediante KVM/libvirt.

---

## Ejecución Rápida con `uv`

No se requiere instalación global. Puedes ejecutar cualquier comando directamente usando `uv`:

```bash
# Ver ayuda global y comandos disponibles
uv run iconshift --help

# Ver versión
uv run iconshift --version
```

---

## Guía de Comandos y Ejemplos

### 1. `scan`: Auditar Iconos de Aplicaciones

#### Ver todos los lanzadores del sistema y cómo se resuelven
```bash
uv run iconshift scan
```

#### Filtrar únicamente los iconos faltantes en ACYLS
```bash
uv run iconshift scan --missing
```

#### Auditar contra otro tema distinto de ACYLS
```bash
uv run iconshift scan --theme Papirus --missing
```

#### Salida delimitada para procesar con herramientas Unix (`cut`, `awk`)
```bash
# Salida en TSV sin cabecera
uv run iconshift scan --missing --format tsv

# Extraer únicamente las rutas de los archivos de origen con cut
uv run iconshift scan --missing --format tsv | cut -f4
```

#### Salida estructurada en JSON
```bash
uv run iconshift scan --missing --format json | jq .
```

---

### 2. `generate`: Generar y Recolorear Iconos

#### Probar en modo simulación (`--dry-run`)
Muestra qué acciones se realizarían sin modificar ni crear ningún archivo en el disco:
```bash
uv run iconshift generate --all --dry-run
```

#### Generar todos los iconos faltantes de ACYLS
Utiliza automáticamente la paleta detectada del tema (`#A0A0A0`):
```bash
uv run iconshift generate --all
```

#### Generar un icono específico por su nombre
```bash
uv run iconshift generate --icon org.gnome.Snapshot
```

#### Generar a partir de un archivo SVG específico
```bash
uv run iconshift generate --file /usr/share/icons/hicolor/scalable/apps/vlc.svg
```

#### Personalizar colores (Monocromo o Bi-tono)
```bash
# Definir color primario personalizado
uv run iconshift generate --icon org.gnome.Snapshot --color "#00FFCC"

# Activar modo bi-tono para preservar volumen y contraste
uv run iconshift generate --all --color "#D0D0D0" --secondary-color "#303030" --two-tone
```

#### Especificar un directorio de salida personalizado
```bash
uv run iconshift generate --all --output-dir ~/mi-tema-test/
```

#### Composición mediante Tuberías (Pipes)
Puedes encadenar la salida del `scan` directamente al `generate`:
```bash
# Pasar solo las rutas resueltas al generador mediante stdin (-)
uv run iconshift scan --missing --format paths | uv run iconshift generate -
```

---

### 3. `palette`: Inspeccionar Paletas de Color

Muestra los colores más utilizados en los SVGs de un tema y calcula los colores primario y secundario recomendados:
```bash
# Inspeccionar el tema ACYLS instalado
uv run iconshift palette --theme ACYLS

# Mostrar los 30 colores más frecuentes
uv run iconshift palette --theme ACYLS --limit 30
```

---

## Aplicar y Refrescar Iconos en GNOME

Una vez que hayas generado tus nuevos iconos en `~/.local/share/icons/ACYLS/scalable/apps/`, actualiza la caché del tema y recarga el entorno:

```bash
# 1. Regenerar caché de iconos del tema del usuario
gtk-update-icon-cache -f ~/.local/share/icons/ACYLS

# 2. Recargar el tema de iconos en GNOME (fuerza el refresco en el dock/launcher)
gsettings set org.gnome.desktop.interface icon-theme 'Adwaita'
gsettings set org.gnome.desktop.interface icon-theme 'ACYLS'
```

---

## Ejecución de Pruebas Automatizadas (Máquina Virtual)

Por directiva de arquitectura, **las pruebas nunca se ejecutan en el sistema host**. Toda la suite se ejecuta en la máquina virtual aislada `ulir-dev`:

```bash
# Encender la VM (si está apagada), sincronizar código y ejecutar pytest con cobertura
./scripts/run_tests_in_vm.sh
```

Para más detalles sobre los scripts de virtualización, consulta [scripts/README.md](scripts/README.md).
