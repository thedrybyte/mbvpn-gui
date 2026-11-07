# Malwarebytes Privacy VPN for Linux

A native Linux desktop client for Malwarebytes Privacy VPN, built with GTK4 and Libadwaita on top of WireGuard.

https://github.com/user-attachments/assets/8387c5f6-2ed9-4fe0-8606-429c3ced08c8

## Features

- **Fast & Native**: GTK4 and Libadwaita interface designed for modern Linux desktops (GNOME, Hyprland, Sway, KDE).
- **WireGuard**: Fast, low-latency connections managed directly via NetworkManager.
- **Kill Switch**: Blocks network leaks if the tunnel drops (using `nftables`).
- **Split Tunneling**: Bypass VPN for designated websites and domain names.
- **System Tray**: StatusNotifierItem tray icon with quick connect/disconnect and recent locations.
- **Simple Login**: Activate with your license key or a 6-character code from your Malwarebytes dashboard.
- **Server Browser**: Search and connect to servers across 36 countries and 62 cities.

---

## Installation

### One-Command Install (Recommended)

Run this in your terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/thedrybyte/Linux-MalwarebytesVPN/main/install.sh | bash
```

This installs system dependencies, the `mbvpn` backend, desktop shortcuts, and configures network permissions.

### Arch Linux (`makepkg`)

```bash
git clone https://github.com/thedrybyte/Linux-MalwarebytesVPN.git
cd Linux-MalwarebytesVPN
makepkg -si
```

### Manual Install

```bash
git clone https://github.com/thedrybyte/Linux-MalwarebytesVPN.git
cd Linux-MalwarebytesVPN
./setup.sh
```

---

## Usage

Launch it from your application menu or run:

```bash
mbvpn-gui
```

To activate your subscription, open **Account and License** in the app and enter your license key or a 6-character MB-code from [my.malwarebytes.com](https://my.malwarebytes.com).

---

## Uninstallation

To uninstall the client:

```bash
curl -fsSL https://raw.githubusercontent.com/thedrybyte/Linux-MalwarebytesVPN/main/uninstall.sh | bash
```

Or from a cloned directory:
```bash
./uninstall.sh
```

*(If installed via `makepkg`, remove with `sudo pacman -R mbvpn-gui`).*

---

## Dependencies

- Python 3 (`python-gobject`, `python-requests`, `python-dbus`)
- GTK4 & Libadwaita
- NetworkManager & WireGuard (`wireguard-tools`)
- `nftables` & `gcc` (for the firewall helper)

On Arch Linux:
```bash
sudo pacman -S --needed python python-gobject python-requests python-dbus gtk4 libadwaita networkmanager wireguard-tools nftables gcc
```

---

## License

GPL-3.0.

*Disclaimer: This is an independent open-source project and is not affiliated with or endorsed by Malwarebytes Inc.*
