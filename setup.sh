#!/usr/bin/env bash
# ==============================================================================
# Malwarebytes Privacy VPN for Linux - Installer & Setup Script
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/mbvpn-gui"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor"

echo "=================================================="
echo "    Malwarebytes Privacy VPN - Linux Client Setup  "
echo "=================================================="

# 0. Check system dependencies
if command -v pacman >/dev/null 2>&1; then
    MISSING_PKGS=()
    for pkg in python python-gobject gtk4 libadwaita networkmanager wireguard-tools nftables python-cairo gcc libcap; do
        if ! pacman -Q "$pkg" >/dev/null 2>&1; then
            MISSING_PKGS+=("$pkg")
        fi
    done
    if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
        echo ":: The following dependencies are missing: ${MISSING_PKGS[*]}"
        echo ":: Install them with:"
        echo "   sudo pacman -S --needed ${MISSING_PKGS[*]}"
        echo ""
    fi
elif command -v apt-get >/dev/null 2>&1; then
    echo ":: Debian/Ubuntu environment detected."
    echo ":: Required dependencies: python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 network-manager wireguard-tools libnftables-dev python3-cairo gcc libcap2-bin"
    echo ":: If you encounter missing packages, install them with:"
    echo "   sudo apt-get install -y python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 network-manager wireguard-tools libnftables-dev python3-cairo gcc libcap2-bin"
    echo ""
elif command -v dnf >/dev/null 2>&1; then
    echo ":: Fedora/RHEL environment detected."
    echo ":: Required dependencies: python3 python3-gobject gtk4 libadwaita NetworkManager wireguard-tools nftables-devel python3-cairo gcc libcap"
    echo ":: If you encounter missing packages, install them with:"
    echo "   sudo dnf install -y python3 python3-gobject gtk4 libadwaita NetworkManager wireguard-tools nftables-devel python3-cairo gcc libcap"
    echo ""
fi

# 1. Ensure official mbvpn WireGuard binary is present
mkdir -p "$BIN_DIR"
MBVPN_BIN="$BIN_DIR/mbvpn"

if [ ! -f "$MBVPN_BIN" ] && ! command -v mbvpn >/dev/null 2>&1; then
    echo ":: Downloading official mbvpn CLI backend..."
    curl -sL https://github.com/Malwarebytes/mbvpn-linux/releases/download/v0.2.1/mbvpn-linux_0.2.1_linux_amd64.tar.gz | tar -xz -C "$BIN_DIR" mbvpn
    chmod +x "$MBVPN_BIN"
    echo "✓ Official mbvpn binary installed to $MBVPN_BIN"
else
    echo "✓ Official mbvpn CLI binary detected."
fi

# 2. Compile and install Linux Kill Switch firewall helper
FW_PATH="$BIN_DIR/mbvpn-firewall"
echo ":: Compiling Linux Kill Switch firewall helper..."
gcc -O2 "$SCRIPT_DIR/firewall.c" -lnftables -o "$FW_PATH"
chmod +x "$FW_PATH"
echo "✓ Firewall helper compiled to $FW_PATH"

# 3. Install application files to ~/.local/share/mbvpn-gui
echo ":: Installing application files to $APP_DIR..."
mkdir -p "$APP_DIR"
cp "$SCRIPT_DIR/app.py" "$SCRIPT_DIR/backend.py" "$SCRIPT_DIR/tray.py" "$APP_DIR/"
rm -rf "$APP_DIR/assets"
cp -r "$SCRIPT_DIR/assets" "$APP_DIR/"

# 4. Install launcher wrapper to ~/.local/bin/mbvpn-gui
cp "$SCRIPT_DIR/bin/mbvpn-gui" "$BIN_DIR/mbvpn-gui"
chmod +x "$BIN_DIR/mbvpn-gui"
echo "✓ Executable launcher installed to $BIN_DIR/mbvpn-gui"

# 5. Install desktop shortcut & multi-resolution icons
echo ":: Installing desktop entry and application icons..."
mkdir -p "$DESKTOP_DIR" "$ICON_DIR/scalable/apps"
cp "$SCRIPT_DIR/mbvpn.svg" "$ICON_DIR/scalable/apps/mbvpn.svg"
cp "$SCRIPT_DIR/org.drybyte.mbvpn.desktop" "$DESKTOP_DIR/org.drybyte.mbvpn.desktop"

for sz in 16 24 32 48 64 128 256 512; do
    mkdir -p "$ICON_DIR/${sz}x${sz}/apps"
    if [ -f "$SCRIPT_DIR/assets/mbvpn_${sz}.png" ]; then
        cp "$SCRIPT_DIR/assets/mbvpn_${sz}.png" "$ICON_DIR/${sz}x${sz}/apps/mbvpn.png"
    fi
done

if [ -d "$HOME/Desktop" ]; then
    cp "$SCRIPT_DIR/org.drybyte.mbvpn.desktop" "$HOME/Desktop/MalwarebytesVPN.desktop"
    chmod +x "$HOME/Desktop/MalwarebytesVPN.desktop"
fi

update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
gtk-update-icon-cache -f -t "$ICON_DIR" 2>/dev/null || true
echo "✓ Desktop launcher and icons installed."

# 6. Check and explain network capabilities & polkit permissions
echo ""
echo ":: Checking Network Capabilities & Permissions..."
RESOLVED_MBVPN="$(command -v mbvpn || echo "$MBVPN_BIN")"
NEED_CAP=0
if ! getcap "$RESOLVED_MBVPN" 2>/dev/null | grep -q "cap_net_admin"; then
    NEED_CAP=1
fi
if ! getcap "$FW_PATH" 2>/dev/null | grep -q "cap_net_admin"; then
    NEED_CAP=1
fi

if [ $NEED_CAP -eq 0 ]; then
    echo "✓ Linux network capabilities already configured."
else
    echo "=================================================================="
    echo "[!] One-time permission setup for zero-password VPN connections:"
    echo "    Run the following command once to grant network administration:"
    echo ""
    echo "    sudo setcap cap_net_admin,cap_net_raw+eip \"$RESOLVED_MBVPN\" cap_net_admin,cap_net_raw+eip \"$FW_PATH\""
    echo "    sudo cp \"$SCRIPT_DIR/10-mbvpn.rules\" /etc/polkit-1/rules.d/ 2>/dev/null || true"
    echo "=================================================================="
fi

echo ""
echo "=== Setup complete! ==="
echo "Launch with: mbvpn-gui"
echo "Or search 'MalwarebytesVPN' in your application launcher."
