# Scripts de Gestión y Testing en Máquina Virtual (`ulir-dev`)

Este directorio contiene los scripts para interactuar con el entorno aislado de pruebas en KVM/libvirt (`ulir-dev`), garantizando que **ninguna prueba unitaria o de integración se ejecute directamente sobre el host**.

---

## Prerrequisitos en el Host
- `virsh` configurado con acceso al hipervisor (`qemu:///system`).
- Red virtual `default` de libvirt activa.
- Clave SSH privada en `~/.ssh/id_rsa` autorizada para el usuario `ulir`.
- Utilidad `rsync` instalada en el host.

---

## Scripts Disponibles

### 1. `vm_status.sh`
Consulta el estado de la máquina virtual `ulir-dev` y muestra su dirección IP si está activa:
```bash
./scripts/vm_status.sh
```

### 2. `vm_start.sh`
Inicia la máquina virtual con `virsh` si está apagada, espera a que adquiera dirección IP vía DHCP/guest-agent y verifica que el puerto SSH (22) responda adecuadamente:
```bash
./scripts/vm_start.sh
```

### 3. `vm_ssh.sh`
Abre una sesión interactiva o ejecuta comandos remotos en la máquina virtual:
```bash
# Sesión interactiva
./scripts/vm_ssh.sh

# Ejecución de un comando específico
./scripts/vm_ssh.sh "uname -a"
```

### 4. `run_tests_in_vm.sh`
**Script principal de testing automatizado.** Realiza el ciclo completo:
1. Enciende la máquina virtual si está apagada.
2. Sincroniza el código fuente y la suite de pruebas hacia `/home/ulir/builds/iconshift_v1.1` en la VM.
3. Asegura la disponibilidad de `uv` dentro de la VM.
4. Ejecuta `pytest --cov=src --cov-report=term-missing tests/` íntegramente dentro del entorno virtualizado.
5. Devuelve la salida y el código de retorno a la terminal del host.

Uso:
```bash
./scripts/run_tests_in_vm.sh
```
