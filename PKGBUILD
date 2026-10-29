# Maintainer: DryByte <thedrybyte@users.noreply.github.com>
pkgname=mbvpn-gui
pkgver=1.0.0
pkgrel=1
pkgdesc="Native GTK4/Libadwaita GUI client for Malwarebytes Privacy VPN on Linux"
arch=('x86_64')
url="https://github.com/thedrybyte/mbvpn-gui"
license=('GPL-3.0-or-later')
depends=(
    'python'
    'python-gobject'
    'gtk4'
    'libadwaita'
    'networkmanager'
    'wireguard-tools'
    'nftables'
    'python-cairo'
)
makedepends=('gcc')
optdepends=(
    'mbvpn: official Malwarebytes WireGuard CLI backend'
    'libayatana-appindicator: fallback system tray indicator support'
)
install=mbvpn-gui.install
source=()

build() {
    local src_path="$startdir"
    if [ -d "$srcdir/$pkgname-$pkgver" ]; then
        src_path="$srcdir/$pkgname-$pkgver"
    fi
    gcc -O2 "$src_path/firewall.c" -lnftables -o mbvpn-firewall
}

package() {
    local src_path="$startdir"
    if [ -d "$srcdir/$pkgname-$pkgver" ]; then
        src_path="$srcdir/$pkgname-$pkgver"
    fi

    # Application files
    install -d "$pkgdir/usr/share/mbvpn-gui"
    install -m644 "$src_path/app.py" "$pkgdir/usr/share/mbvpn-gui/"
    install -m644 "$src_path/backend.py" "$pkgdir/usr/share/mbvpn-gui/"
    install -m644 "$src_path/tray.py" "$pkgdir/usr/share/mbvpn-gui/"
    cp -r "$src_path/assets" "$pkgdir/usr/share/mbvpn-gui/"

    # Binaries
    install -d "$pkgdir/usr/bin"
    install -m755 "$src_path/bin/mbvpn-gui" "$pkgdir/usr/bin/mbvpn-gui"
    install -m755 mbvpn-firewall "$pkgdir/usr/bin/mbvpn-firewall"

    # Desktop entry & Icons
    install -Dm644 "$src_path/org.paradoxbyte.mbvpn.desktop" "$pkgdir/usr/share/applications/org.paradoxbyte.mbvpn.desktop"
    install -Dm644 "$src_path/mbvpn.svg" "$pkgdir/usr/share/icons/hicolor/scalable/apps/mbvpn.svg"
    for sz in 16 24 32 48 64 128 256 512; do
        if [ -f "$src_path/assets/mbvpn_${sz}.png" ]; then
            install -Dm644 "$src_path/assets/mbvpn_${sz}.png" "$pkgdir/usr/share/icons/hicolor/${sz}x${sz}/apps/mbvpn.png"
        fi
    done

    # Polkit rules for passwordless DNS routing
    install -Dm644 "$src_path/10-mbvpn.rules" "$pkgdir/usr/share/polkit-1/rules.d/10-mbvpn.rules"

    # License
    if [ -f "$src_path/LICENSE" ]; then
        install -Dm644 "$src_path/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
    fi
}
