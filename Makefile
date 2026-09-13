.DEFAULT_GOAL := help

.PHONY: all build install package test clean vm-start vm-status vm-ssh aur-update help

help:
	@echo "IconShift - Automation & Build Interface"
	@echo ""
	@echo "Available targets:"
	@echo "  make build       Build standalone Linux binary in dist/iconshift via PyInstaller"
	@echo "  make install     Install built binary into \$$HOME/.local/bin/iconshift"
	@echo "  make package     Package binary into release/ tarball and generate SHA-256"
	@echo "  make test        Execute full test suite with coverage inside isolated VM"
	@echo "  make clean       Remove build, dist, and release artifacts safely"
	@echo "  make vm-start    Start the 'ulir-dev' testing virtual machine and wait for SSH"
	@echo "  make vm-status   Query current status and IP address of 'ulir-dev' VM"
	@echo "  make vm-ssh      Open interactive SSH session into 'ulir-dev' VM"
	@echo "  make aur-update  Update PKGBUILD version and checksum, regenerate .SRCINFO"
	@echo ""

all: build

build:
	@bash scripts/build/build.sh

install:
	@bash scripts/build/install.sh

package:
	@bash scripts/build/package.sh

test:
	@bash scripts/test/run_tests_in_vm.sh

clean:
	@echo "Cleaning generated build, dist, and release artifacts..."
	@rm -rf build/ dist/ release/ *.spec
	@echo "Clean completed."

vm-start:
	@bash scripts/vm/vm_start.sh

vm-status:
	@bash scripts/vm/vm_status.sh

vm-ssh:
	@bash scripts/vm/vm_ssh.sh

aur-update:
	@bash scripts/release/update_aur.sh
