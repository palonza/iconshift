# Scripts de Automatización y Tooling - IconShift

Este directorio centraliza las herramientas y automatizaciones del ciclo de vida de **IconShift**, organizadas por áreas de responsabilidad:

```text
scripts/
├── build/
│   ├── build.sh         # Compila el ejecutable independiente en dist/iconshift
│   ├── install.sh       # Instala el binario en $HOME/.local/bin/iconshift
│   └── package.sh       # Empaqueta en release/ con checksum SHA-256
├── test/
│   └── run_tests_in_vm.sh  # Ejecuta la suite con cobertura en la VM aislada
├── release/
│   └── update_aur.sh    # Prepara actualizaciones de PKGBUILD y .SRCINFO para AUR
└── vm/
    ├── vm_start.sh      # Inicia la VM ulir-dev y espera al servicio SSH
    ├── vm_status.sh     # Consulta estado e IP de la VM
    └── vm_ssh.sh        # Sesión interactiva / comandos remotos por SSH
```

---

## 1. Build del Ejecutable Linux (`scripts/build/build.sh`)
Genera un único binario ejecutable autocontenido en `dist/iconshift` utilizando PyInstaller a través de `uv` (sin añadirlo a las dependencias de runtime).
- Resuelve correctamente el paquete `src/iconshift`.
- Limpia de forma segura los artefactos intermedios previos.
- Valida permisos y realiza un chequeo funcional (`--version` y `--help`).

```bash
# Ejecución directa
bash scripts/build/build.sh

# Vía Makefile
make build
```

---

## 2. Instalación Local (`scripts/build/install.sh`)
Instala el binario compilado en `$HOME/.local/bin/iconshift` utilizando `install -Dm755` sin requerir `sudo`.
- Comprueba que el ejecutable exista antes de proceder.

```bash
# Ejecución directa
bash scripts/build/install.sh

# Vía Makefile
make install
```

---

## 3. Generación de Paquete Distribuible (`scripts/build/package.sh`)
Empaqueta el ejecutable junto con la documentación (`README.md`, `LICENSE`) en un archivo comprimido estándar:
- Nombre generado dinámicamente: `release/iconshift-<version>-linux-<arch>.tar.gz`
- Genera el archivo de suma de comprobación SHA-256: `release/iconshift-<version>-linux-<arch>.tar.gz.sha256`

```bash
# Ejecución directa
bash scripts/build/package.sh

# Vía Makefile
make package
```

---

## 4. Ejecución de Tests en Máquina Virtual (`scripts/test/run_tests_in_vm.sh`)
Por directiva estricta de arquitectura, **las pruebas nunca se ejecutan en el host**.
- Inicia la VM `ulir-dev` si se encuentra apagada.
- Sincroniza el código a la VM mediante streaming `tar` sobre SSH.
- Ejecuta `uv run pytest --cov=src --cov-report=term-missing tests/` de forma completamente aislada.

```bash
# Ejecución directa
bash scripts/test/run_tests_in_vm.sh

# Vía Makefile
make test
```

---

## 5. Preparación de Release para AUR (`scripts/release/update_aur.sh`)
Herramienta de soporte para mantener el paquete de Arch User Repository (AUR).
- Puede recibir versión (`--version`) y checksum (`--sha256`), o detectarlos automáticamente desde el último paquete generado en `release/`.
- Actualiza `pkgver`, reinicia `pkgrel=1` y actualiza `sha256sums` en el `PKGBUILD`.
- Regenera el archivo `.SRCINFO` con `makepkg --printsrcinfo > .SRCINFO`.
- **Seguridad:** No almacena credenciales ni ejecuta `git push`; los cambios quedan preparados para revisión manual.

```bash
# Preparar actualización usando los artefactos locales de release/
bash scripts/release/update_aur.sh --pkgbuild packaging/aur/PKGBUILD

# O con parámetros explícitos
bash scripts/release/update_aur.sh --version 1.1.0 --sha256 <HASH> --dir /path/to/aur-repo

# Vía Makefile
make aur-update
```

---

## 6. Gestión de la Máquina Virtual (`scripts/vm/`)
Comandos auxiliares para interactuar con el entorno de pruebas KVM/libvirt:

```bash
# Consultar estado e IP de la VM
make vm-status
# o: bash scripts/vm/vm_status.sh

# Iniciar la VM y esperar disponibilidad de SSH
make vm-start
# o: bash scripts/vm/vm_start.sh

# Abrir sesión interactiva por SSH
make vm-ssh
# o: bash scripts/vm/vm_ssh.sh
```

---

## 7. Limpieza de Artefactos Generados
Elimina de manera segura únicamente los directorios y archivos producidos por el build y packaging (`build/`, `dist/`, `release/`, `*.spec`):

```bash
make clean
```
