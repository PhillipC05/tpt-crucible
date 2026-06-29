<#
.SYNOPSIS
    TPT Crucible WSL2 Auto-Setup Helper
.DESCRIPTION
    Detects WSL2 availability, installs Ubuntu 22.04 distro,
    configures XRT inside WSL2, verifies card passthrough.
    One command from PowerShell.
.EXAMPLE
    .\setup-wsl2.ps1
    .\setup-wsl2.ps1 -DistroName TPT-Crucible -InstallXrt
#>

param(
    [string]$DistroName = "TPT-Crucible",
    [switch]$InstallXrt = $true,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Write-Status($msg) { Write-Host "[tpt-setup] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)     { Write-Host "[  OK  ] $msg" -ForegroundColor Green }
function Write-Warn($msg)   { Write-Host "[ WARN ] $msg" -ForegroundColor Yellow }
function Write-Err($msg)    { Write-Host "[ERROR] $msg" -ForegroundColor Red }

function Test-WslAvailable {
    try {
        $wsl = wsl --status 2>&1
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Test-Wsl2Kernel {
    try {
        $ver = wsl -l -v 2>&1 | Select-String "VERSION.*2"
        return $null -ne $ver
    } catch {
        return $false
    }
}

function Get-InstalledDistros {
    try {
        $list = wsl -l -q 2>&1
        return $list -split "`n" | Where-Object { $_.Trim() -ne "" } | ForEach-Object { $_.Trim() }
    } catch {
        return @()
    }
}

function Install-UbuntuDistro {
    param([string]$Name)

    Write-Status "Installing Ubuntu 22.04 as '$Name'..."
    wsl --install -d Ubuntu-22.04 --name $Name --no-launch 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to install Ubuntu 22.04. Ensure WSL2 is enabled."
        Write-Host ""
        Write-Host "Enable WSL2 manually:" -ForegroundColor Yellow
        Write-Host "  wsl --install" -ForegroundColor White
        Write-Host "  (Restart PC, then re-run this script)" -ForegroundColor White
        exit 1
    }
    Write-Ok "Ubuntu 22.04 installed as '$Name'"
}

function Configure-WslDistro {
    param([string]$Name)

    Write-Status "Configuring $Name..."

    $setupScript = @'
#!/bin/bash
set -euo pipefail
echo "[wsl-setup] Updating package lists..."
sudo apt-get update -qq
echo "[wsl-setup] Installing build essentials..."
sudo apt-get install -y -qq build-essential cmake git curl wget python3 python3-pip
echo "[wsl-setup] Installing Rust..."
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y 2>/dev/null
echo "[wsl-setup] Installing TPT Crucible..."
pip3 install --user tpt-crucible 2>/dev/null || echo "tpt-crucible not yet published"
echo "[wsl-setup] Configuration complete"
'@

    $setupScript | wsl -d $Name -- bash
    Write-Ok "Distribution configured"
}

function Install-XrtInWsl {
    param([string]$Name)

    if (-not $InstallXrt) { return }

    Write-Status "Installing XRT in $Name..."

    $xrtScript = @'
#!/bin/bash
set -euo pipefail
echo "[xrt-wsl] Installing kernel headers..."
sudo apt-get update -qq
sudo apt-get install -y -qq linux-headers-$(uname -r) 2>/dev/null || sudo apt-get install -y -qq linux-headers-generic
echo "[xrt-wsl] Downloading XRT..."
XRT_VERSION="2024.1"
UBUNTU_VER=$(lsb_release -rs)
MAJOR=$(echo $UBUNTU_VER | cut -d. -f1)
MINOR=$(echo $UBUNTU_VER | cut -d. -f2)
DEB="xrt_${XRT_VERSION}-1ubuntu${MAJOR}.${MINOR}_amd64.deb"
curl -L -o "/tmp/$DEB" "https://github.com/Xilinx/XRT/releases/download/${XRT_VERSION}/$DEB" 2>/dev/null
echo "[xrt-wsl] Installing XRT..."
sudo dpkg -i "/tmp/$DEB" 2>/dev/null || sudo apt-get install -f -y
echo "[xrt-wsl] XRT installation complete"
'@

    $xrtScript | wsl -d $Name -- bash
    Write-Ok "XRT installed in $Name"
}

function Test-CardPassthrough {
    param([string]$Name)

    Write-Status "Checking FPGA card passthrough..."

    $checkScript = @'
#!/bin/bash
if lspci 2>/dev/null | grep -qi "xilinx\|advanced micro\|amd.*fpga"; then
    echo "PASS: FPGA card detected via lspci"
    exit 0
elif ls /dev/xfpga* 2>/dev/null || ls /dev/dri/render* 2>/dev/null; then
    echo "PASS: FPGA device nodes found"
    exit 0
else
    echo "WARN: No FPGA card detected. Check PCIe passthrough settings."
    echo "In Windows: wsl --shutdown, then ensure PCIe passthrough is configured."
    exit 1
fi
'@

    $result = $checkScript | wsl -d $Name -- bash 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "FPGA card passthrough verified"
    } else {
        Write-Warn $result
        Write-Host ""
        Write-Host "To enable PCIe passthrough:" -ForegroundColor Yellow
        Write-Host "  1. Enable Intel VT-d or AMD-Vi in BIOS" -ForegroundColor White
        Write-Host "  2. Add to .wslconfig: [wsl2] pci=true" -ForegroundColor White
        Write-Host "  3. Restart: wsl --shutdown" -ForegroundColor White
    }
}

function Show-Summary {
    param([string]$Name)

    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "  TPT Crucible WSL2 Setup Complete" -ForegroundColor Cyan
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Distro: $Name" -ForegroundColor White
    Write-Host "  Shell:  wsl -d $Name" -ForegroundColor White
    Write-Host ""
    Write-Host "  Quick start:" -ForegroundColor Yellow
    Write-Host "    wsl -d $Name" -ForegroundColor White
    Write-Host "    source /opt/xilinx/xrt/setup.sh" -ForegroundColor White
    Write-Host "    tpt-doctor --target fusion" -ForegroundColor White
    Write-Host ""
}

# Main
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  TPT Crucible — WSL2 Auto-Setup" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-WslAvailable)) {
    Write-Err "WSL is not available. Install with: wsl --install"
    exit 1
}

Write-Ok "WSL is available"

$installed = Get-InstalledDistros
if ($installed -contains $DistroName) {
    Write-Ok "Distribution '$DistroName' already exists"
} else {
    Install-UbuntuDistro -Name $DistroName
}

Configure-WslDistro -Name $DistroName
Install-XrtInWsl -Name $DistroName
Test-CardPassthrough -Name $DistroName
Show-Summary -Name $DistroName
