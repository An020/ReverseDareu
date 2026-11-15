# Maintainer: Omarchy Team <support@omarchy.org>
pkgname=dareu-control
pkgver=1.5.6.16
pkgrel=3
pkgdesc="Daemon and native Omarchy desktop control center for DAREU gaming peripherals"
arch=('any')
url="https://github.com/omacom/ReverseDareu"
license=('GPL3')
depends=('python' 'tk')
optdepends=(
    'wine: Run original Windows utility via dareu-wine-runner for firmware updates'
    'wine-mono: .NET runtime for Wine execution'
)
install=dareu.install

package() {
    cd "${srcdir}/.."

    # 1. Python libraries
    install -dm755 "${pkgdir}/usr/lib/dareu"
    install -m644 daemon/protocol.py "${pkgdir}/usr/lib/dareu/protocol.py"
    install -m644 daemon/hid_interface.py "${pkgdir}/usr/lib/dareu/hid_interface.py"

    # 2. Executable binaries and wrappers
    install -dm755 "${pkgdir}/usr/bin"
    
    # Daemon executable
    cat << 'EOF' > "${pkgdir}/usr/bin/dareud"
#!/usr/bin/env bash
export PYTHONPATH="/usr/lib/dareu:${PYTHONPATH:-}"
exec python3 -u /usr/lib/dareu/dareud.py "$@"
EOF
    chmod 755 "${pkgdir}/usr/bin/dareud"
    install -m755 daemon/dareud.py "${pkgdir}/usr/lib/dareu/dareud.py"

    # GUI executable
    cat << 'EOF' > "${pkgdir}/usr/bin/dareu-control"
#!/usr/bin/env bash
export PYTHONPATH="/usr/lib/dareu:${PYTHONPATH:-}"
exec python3 /usr/lib/dareu/dareu_app.py "$@"
EOF
    chmod 755 "${pkgdir}/usr/bin/dareu-control"
    install -m755 ui/dareu_app.py "${pkgdir}/usr/lib/dareu/dareu_app.py"

    # Wine fallback runner
    install -m755 wine/dareu-wine-runner.sh "${pkgdir}/usr/bin/dareu-wine-runner"

    # 3. Hardware udev rules (70- runs before systemd 73-seat-late.rules)
    install -dm755 "${pkgdir}/usr/lib/udev/rules.d"
    install -m644 udev/99-dareu.rules "${pkgdir}/usr/lib/udev/rules.d/70-dareu.rules"
    install -m644 udev/99-dareu.rules "${pkgdir}/usr/lib/udev/rules.d/99-dareu.rules"

    # 4. Systemd user service + Autostart target link
    install -dm755 "${pkgdir}/usr/lib/systemd/user"
    install -m644 systemd/dareu.service "${pkgdir}/usr/lib/systemd/user/dareu.service"
    install -dm755 "${pkgdir}/usr/lib/systemd/user/default.target.wants"
    ln -s "../dareu.service" "${pkgdir}/usr/lib/systemd/user/default.target.wants/dareu.service"

    # 5. XDG Autostart entry
    install -dm755 "${pkgdir}/etc/xdg/autostart"
    install -m644 autostart/dareu-autostart.desktop "${pkgdir}/etc/xdg/autostart/dareu-autostart.desktop"

    # 6. Desktop entry and icons
    install -dm755 "${pkgdir}/usr/share/applications"
    install -m644 desktop/dareu.desktop "${pkgdir}/usr/share/applications/dareu.desktop"

    install -dm755 "${pkgdir}/usr/share/icons/hicolor/64x64/apps"
    install -m644 desktop/dareu.png "${pkgdir}/usr/share/icons/hicolor/64x64/apps/dareu.png"

    # 7. Documentation
    install -dm755 "${pkgdir}/usr/share/doc/dareu"
    install -m644 docs/DAREU_PROTOCOL_SPEC.md "${pkgdir}/usr/share/doc/dareu/DAREU_PROTOCOL_SPEC.md"
    install -m644 docs/DISASSEMBLY_FINDINGS.md "${pkgdir}/usr/share/doc/dareu/DISASSEMBLY_FINDINGS.md"
}
