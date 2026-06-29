#!/usr/bin/env bash
# XRT (Xilinx Runtime) one-line installer for TPT Crucible
# Handles Ubuntu version detection, kernel headers, XRT deb install, card detection
# Target: <15 minutes on a clean Ubuntu LTS
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[xrt-install]${NC} $1"; }
ok() { echo -e "${GREEN}[  OK  ]${NC} $1"; }
warn() { echo -e "${YELLOW}[ WARN ]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

XRT_VERSION="${XRT_VERSION:-2024.1}"

detect_ubuntu_version() {
    if [ ! -f /etc/os-release ]; then
        err "Cannot detect OS. Only Ubuntu is supported."
    fi
    . /etc/os-release
    if [ "$ID" != "ubuntu" ]; then
        err "Only Ubuntu is supported. Detected: $ID"
    fi
    echo "$VERSION_ID"
}

install_kernel_headers() {
    log "Installing kernel headers..."
    if dpkg -l | grep -q linux-headers-$(uname -r); then
        ok "Kernel headers already installed"
        return
    fi
    sudo apt-get update -qq
    sudo apt-get install -y -qq linux-headers-$(uname -r) || {
        warn "Could not install headers for $(uname -r), trying generic..."
        sudo apt-get install -y -qq linux-headers-generic
    }
    ok "Kernel headers installed"
}

download_xrt() {
    local ubuntu_ver="$1"
    local major minor
    major=$(echo "$ubuntu_ver" | cut -d. -f1)
    minor=$(echo "$ubuntu_ver" | cut -d. -f2)

    local deb_name="xrt_${XRT_VERSION}-1ubuntu${major}.${minor}_amd64.deb"
    local url="https://github.com/Xilinx/XRT/releases/download/${XRT_VERSION}/${deb_name}"

    log "Downloading XRT ${XRT_VERSION} for Ubuntu ${ubuntu_ver}..."
    if [ -f "/tmp/${deb_name}" ]; then
        ok "XRT deb already downloaded"
        return
    fi
    curl -L -o "/tmp/${deb_name}" "$url" || {
        err "Failed to download XRT. URL: $url"
    }
    ok "XRT downloaded"
}

install_xrt() {
    local ubuntu_ver="$1"
    local major minor
    major=$(echo "$ubuntu_ver" | cut -d. -f1)
    minor=$(echo "$ubuntu_ver" | cut -d. -f2)

    local deb_name="xrt_${XRT_VERSION}-1ubuntu${major}.${minor}_amd64.deb"
    local deb_path="/tmp/${deb_name}"

    if [ ! -f "$deb_path" ]; then
        download_xrt "$ubuntu_ver"
    fi

    log "Installing XRT..."
    sudo dpkg -i "$deb_path" || {
        warn "dpkg failed, attempting dependency resolution..."
        sudo apt-get install -f -y
        sudo dpkg -i "$deb_path"
    }

    sudo apt-get install -y -qq python3-xrt 2>/dev/null || true

    ok "XRT installed"
}

detect_fpga_card() {
    log "Detecting FPGA cards..."
    if command -v xbutil &> /dev/null; then
        xbutil examine 2>/dev/null && ok "FPGA card detected via xbutil" || warn "No card detected by xbutil"
    elif lspci 2>/dev/null | grep -qi "xilinx\|advanced micro\|amd.*fpga"; then
        ok "FPGA card detected via lspci"
    else
        warn "No FPGA card detected (card may not be present or drivers may need reboot)"
    fi
}

verify_installation() {
    log "Verifying installation..."
    local errors=0

    if [ -f /opt/xilinx/xrt/setup.sh ]; then
        ok "XRT setup.sh found"
    else
        warn "XRT setup.sh not found at /opt/xilinx/xrt/setup.sh"
        errors=$((errors + 1))
    fi

    if ldconfig -p 2>/dev/null | grep -q libxrt; then
        ok "XRT library found in ldconfig"
    else
        warn "XRT library not in ldconfig path"
        errors=$((errors + 1))
    fi

    return $errors
}

main() {
    echo ""
    echo "========================================="
    echo "  TPT Crucible — XRT Installer"
    echo "========================================="
    echo ""

    local ubuntu_ver
    ubuntu_ver=$(detect_ubuntu_version)
    log "Detected: Ubuntu $ubuntu_ver"

    install_kernel_headers
    download_xrt "$ubuntu_ver"
    install_xrt "$ubuntu_ver"
    detect_fpga_card

    if verify_installation; then
        echo ""
        ok "XRT installation complete!"
        echo ""
        echo "Next steps:"
        echo "  1. Source XRT setup: source /opt/xilinx/xrt/setup.sh"
        echo "  2. Run tpt-doctor: tpt-doctor --target fusion"
        echo "  3. Connect your FPGA board and run: xbutil examine"
    else
        echo ""
        warn "Installation completed with warnings. Check output above."
        echo "Try: source /opt/xilinx/xrt/setup.sh && tpt-doctor"
    fi
}

main "$@"
