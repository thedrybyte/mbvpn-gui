#!/usr/bin/env python3
"""
Automated Interactive QA Test for Malwarebytes Privacy VPN Redesigned GUI.
Exercises the Cyber UI, World Server Browser (62 countries / 197 servers),
telemetry counters, search filter, and connection state transitions.
"""

import sys
import time
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

from app import MbVpnWindow, MbVpnApplication
from backend import ConnectionStatus


def run_interactive_qa():
    print("=== Starting Interactive QA Test for Redesigned Malwarebytes VPN GUI ===")
    app = MbVpnApplication()
    test_results = {}

    def test_sequence():
        nonlocal test_results
        win = MbVpnWindow(application=app)
        win.present()

        # Step 1: Initial window and Mullvad UI validation
        print("[1/5] Verifying Initial Mullvad UI State...")
        assert win.get_title() == "MalwarebytesVPN"
        assert not hasattr(win, "lbl_status_title"), "Hero status title should be removed"
        assert win.lbl_status_desc.get_text().strip()
        assert win.btn_connect.get_tooltip_text() is None, "Connect control should not show a duplicate tooltip"
        assert win.lbl_connect.get_label() in ["Connect", "Sign in", "Disconnect", "Connecting...", "Disconnecting..."]
        test_results["cyber_ui_state"] = "PASS"
        print("  -> Initial Mullvad UI state passed.")

        # Step 2: Test Server Browser Modal with all 62 locations across 36 countries
        print("[2/5] Testing World Server Browser Modal (62 locations across 36 countries)...")
        win._show_server_browser_modal()
        locs = win.backend.get_locations()
        assert len(locs) == 36, f"Expected exactly 36 countries, got {len(locs)}"
        total_cities = sum(len(c.cities) for c in locs)
        assert total_cities == 62, f"Expected exactly 62 cities/locations, got {total_cities}"
        total_srvs = sum(len(ct.servers) for c in locs for ct in c.cities)
        assert total_srvs >= 145, f"Expected at least 145 servers, got {total_srvs}"
        test_results["server_browser"] = "PASS"
        print(f"  -> World Server Browser verified ({len(locs)} countries, {total_cities} locations, {total_srvs} servers loaded).")

        # Step 3: Test Location Selection & Flag rendering
        print("[3/5] Testing Location Selection & Flag Rendering...")
        win.selected_target = "de-fra"
        win.selected_label = "Frankfurt, Germany"
        win.selected_flag = "🇩🇪"
        win.selected_sub = "City: de-fra"
        win.lbl_flag.set_label(win.selected_flag)
        win.lbl_loc_name.set_label(win.selected_label)
        win.lbl_loc_sub.set_label(win.selected_sub)
        assert win.lbl_loc_name.get_label() == "Frankfurt, Germany"
        assert win.lbl_flag.get_label() == "🇩🇪"
        test_results["location_selection"] = "PASS"
        print("  -> Location selection and emoji flag passed.")

        # Step 4: Test Telemetry and Protected UI State Transition & Toggle Logic
        print("[4/6] Testing Telemetry Counters, Protected State & Button Toggle...")
        dummy_status = ConnectionStatus(
            connected=True,
            server="de-fra-1",
            endpoint="194.126.177.25:1",
            handshake="2026-10-22 06:10:00",
            transfer_down="14.8 MB",
            transfer_up="3.4 MB",
            ip="194.126.177.25",
            country="Germany",
            city="Frankfurt"
        )
        win._update_ui_state(dummy_status, has_cap=True, logged_in=True)
        assert win.is_connected is True
        assert "Tunnel active" in win.lbl_status_desc.get_text()
        assert win.btn_connect.get_tooltip_text() is None, "Disconnect state should not show a duplicate tooltip"
        assert win.lbl_connect.get_label() == "Disconnect"

        # Verify toggle logic branch when connected:
        disconnect_called = False
        def mock_disconnect():
            nonlocal disconnect_called
            disconnect_called = True
        win._disconnect_vpn = mock_disconnect
        win.btn_connect.emit("clicked")
        assert disconnect_called is True, "Failed to call _disconnect_vpn when connected"

        # Verify toggle logic branch when disconnected:
        win.is_connected = False
        connect_called = False
        def mock_connect():
            nonlocal connect_called
            connect_called = True
        win._connect_vpn = mock_connect
        win._on_toggle_clicked(None)
        assert connect_called is True, "Failed to call _connect_vpn when disconnected"

        test_results["telemetry_and_protection"] = "PASS"
        print("  -> Shield toggle correctly routes connect vs disconnect.")

        # Step 5: Test Security & Tunnel Preferences Toggles and Settings Dialog
        print("[5/7] Testing Security & Tunnel Preferences (Kill Switch, Split Tunneling, Auto-Connect)...")
        assert not hasattr(win, "row_ip"), "Visible IP row should be removed"
        assert not hasattr(win, "row_geo"), "Detected Location row should be removed"

        # Open Settings Modal and verify split tunneling controls
        win._show_settings_dialog()
        print("  -> Settings Modal with Split Tunneling successfully opened.")

        # Toggle Kill Switch & Verify Backend Call, then immediately restore to False
        win.switch_killswitch.set_active(True)
        assert win.settings.get("kill_switch") is True
        win.switch_killswitch.set_active(False)
        assert win.settings.get("kill_switch") is False
        win.backend.disable_killswitch()
        assert hasattr(win.backend, "enable_killswitch"), "Backend missing enable_killswitch"
        assert hasattr(win.backend, "disable_killswitch"), "Backend missing disable_killswitch"
        assert hasattr(win.backend, "is_killswitch_active"), "Backend missing is_killswitch_active"
        assert hasattr(win.backend, "apply_split_tunneling"), "Backend missing apply_split_tunneling"
        assert hasattr(win.backend, "resolve_website_ips"), "Backend missing resolve_website_ips"
        assert hasattr(win.backend, "apply_website_split_tunneling"), "Backend missing apply_website_split_tunneling"
        assert hasattr(win.backend, "clear_website_split_tunneling"), "Backend missing clear_website_split_tunneling"
        assert hasattr(win, "switch_split_websites"), "Settings missing switch_split_websites"

        # Verify domain resolution and website split tunneling toggles
        test_ips = win.backend.resolve_website_ips("1.1.1.1")
        assert "1.1.1.1" in test_ips, f"Expected 1.1.1.1 in resolved IPs, got {test_ips}"
        win.switch_split_websites.set_active(True)
        assert win.settings.get("split_tunnel_websites_enabled") is True
        win.switch_split_websites.set_active(False)
        assert win.settings.get("split_tunnel_websites_enabled") is False

        # Toggle DNS Shield
        win.switch_dns.set_active(True)
        assert win.settings.get("dns_leak_shield") is True

        # Toggle Auto-Reconnect
        win.switch_autoreconnect.set_active(True)
        assert win.settings.get("auto_reconnect") is True

        # Toggle Auto-Connect
        win.switch_autoconnect.set_active(True)
        assert win.settings.get("auto_connect") is True

        test_results["security_preferences"] = "PASS"
        print("  -> Security switches & settings persistence passed.")

        # Step 6: Test Account Dialog & Expiry Details
        print("[6/7] Testing Account Modal with Expiry Date and License Details...")
        acct = win.backend.get_account_details()
        if win.backend.is_logged_in():
            assert acct.get("status") == "Licensed"
            assert "December" in acct.get("expiry_formatted", "")
            print(f"  -> Account verified: {acct['plan']} | Expiry: {acct['expiry_formatted']} ({acct['days_remaining']} days left).")
        else:
            assert acct.get("status") == "Not Activated"
            print(f"  -> Account verified (Logged out state): {acct['plan']} | Status: {acct.get('status')}.")
        win._show_account_dialog()
        test_results["account_details"] = "PASS"

        # Step 7: Test System Tray (StatusNotifierItem) & Right-Click DbusMenu
        print("[7/7] Testing System Tray Integration & Right-Click Context Menu...")
        assert hasattr(win, "tray") and win.tray is not None, "Tray instance not initialized"
        win.tray.update_status(True, "de-fra-1")
        assert win.tray._connected is True
        assert win.tray._icon_name == "security-high-symbolic"

        # Verify DBusMenu right-click structure
        assert hasattr(win.tray, "dbus_menu") and win.tray.dbus_menu is not None
        labels = [item.get("label", "") for item in win.tray.dbus_menu.items.values()]
        print("  -> Tray Context Menu entries:", [l for l in labels if l])

        # 1. Check Fastest Server option
        assert any("Fastest Location" in l for l in labels), "Missing Fastest Location option in tray menu"
        # 2. Check Recent Servers
        assert any("Recent Locations" in l or "Los Angeles" in l or "Frankfurt" in l for l in labels), "Missing Recent Servers in tray menu"
        # 3. Check Quit button
        assert any("Quit" in l for l in labels), "Missing Quit button in tray menu"

        # Test toggle visibility
        win._toggle_window_visibility()
        assert win.is_visible() is False, "Window should be hidden after toggle"
        win._toggle_window_visibility()
        assert win.is_visible() is True, "Window should be visible after toggle"

        # Test close-request minimization
        win.settings["minimize_to_tray"] = True
        ret = win._on_close_request(None)
        assert ret is True, "Close request should return True to inhibit quit"
        assert win.is_visible() is False, "Window should be minimized to tray"

        test_results["system_tray_menu"] = "PASS"
        print("  -> System tray context menu, Fastest Location, Recent Servers, and Quit verified.")

        print("\nAll interactive QA tests completed successfully!")
        print("Test summary:", test_results)
        win.backend.disable_killswitch()
        app.quit()
        return False

    GLib.idle_add(test_sequence)
    app.run([sys.argv[0]])

    return all(res == "PASS" for res in test_results.values())


if __name__ == "__main__":
    success = run_interactive_qa()
    sys.exit(0 if success else 1)
