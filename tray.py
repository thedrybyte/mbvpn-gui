#!/usr/bin/env python3
"""
Native StatusNotifierItem (SNI) and DBusMenu Service for Malwarebytes Privacy VPN.
Zero extra dependencies (uses GLib and D-Bus).
Provides dynamic icon, tooltip, and full native right-click context menu:
- Fastest Location (Auto)
- Recently Connected Servers list
- Open Dashboard
- Quick Connect / Disconnect toggle
- Quit Application
"""

import os
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
from typing import Any, Callable, Dict, List, Optional, Tuple

SNI_INTERFACE = "org.kde.StatusNotifierItem"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
DBUSMENU_INTERFACE = "com.canonical.dbusmenu"


class DbusMenu(dbus.service.Object):
    def __init__(self, bus_name: dbus.service.BusName, path: str = "/MenuBar"):
        super().__init__(bus_name, path)
        self.revision = 1
        self.items: Dict[int, Dict[str, Any]] = {}
        self.callbacks: Dict[int, Callable[[], None]] = {}

    def set_menu_structure(self, items: List[Dict[str, Any]]):
        """
        items is a list of dicts:
        {"id": 1, "label": "Text", "type": "standard"|"separator", "enabled": True, "action": callable}
        """
        self.items.clear()
        self.callbacks.clear()
        self.items[0] = {"id": 0, "type": "root", "children": []}

        for item in items:
            item_id = item["id"]
            self.items[item_id] = item
            self.items[0]["children"].append(item_id)
            if "action" in item and item["action"]:
                self.callbacks[item_id] = item["action"]

        self.revision += 1
        self.LayoutUpdated(dbus.UInt32(self.revision), dbus.Int32(0))

    def _build_layout(self, item_id: int):
        item = self.items.get(item_id, {})
        props = dbus.Dictionary({}, signature="sv")

        item_type = item.get("type", "standard")
        if item_type == "separator":
            props["type"] = dbus.String("separator", variant_level=1)
        elif item_id != 0:
            props["label"] = dbus.String(item.get("label", ""), variant_level=1)
            props["enabled"] = dbus.Boolean(item.get("enabled", True), variant_level=1)
            props["visible"] = dbus.Boolean(True, variant_level=1)
            if item.get("icon-name"):
                props["icon-name"] = dbus.String(item["icon-name"], variant_level=1)

        children_ids = item.get("children", [])
        children_array = dbus.Array([], signature="v")
        for cid in children_ids:
            child_struct = self._build_layout(cid)
            children_array.append(dbus.Struct(child_struct, signature="(ia{sv}av)"))

        return (dbus.Int32(item_id), props, children_array)

    # --- com.canonical.dbusmenu Methods ---

    @dbus.service.method(DBUSMENU_INTERFACE, in_signature="iias", out_signature="u(ia{sv}av)")
    def GetLayout(self, parentId: int, recursionDepth: int, propertyNames: List[str]):
        layout = self._build_layout(0)
        return (dbus.UInt32(self.revision), layout)

    @dbus.service.method(DBUSMENU_INTERFACE, in_signature="aias", out_signature="a(ia{sv})")
    def GetGroupProperties(self, ids: List[int], propertyNames: List[str]):
        res = dbus.Array([], signature="(ia{sv})")
        for item_id in ids:
            item = self.items.get(item_id)
            if item:
                props = dbus.Dictionary({}, signature="sv")
                if item.get("type") == "separator":
                    props["type"] = dbus.String("separator", variant_level=1)
                elif item_id != 0:
                    props["label"] = dbus.String(item.get("label", ""), variant_level=1)
                    props["enabled"] = dbus.Boolean(item.get("enabled", True), variant_level=1)
                    props["visible"] = dbus.Boolean(True, variant_level=1)
                res.append(dbus.Struct((dbus.Int32(item_id), props), signature="(ia{sv})"))
        return res

    @dbus.service.method(DBUSMENU_INTERFACE, in_signature="isvu", out_signature="")
    def Event(self, item_id: int, eventId: str, data: Any, timestamp: int):
        if eventId == "clicked":
            action = self.callbacks.get(item_id)
            if action:
                GLib.idle_add(action)

    @dbus.service.method(DBUSMENU_INTERFACE, in_signature="i", out_signature="b")
    def AboutToShow(self, item_id: int):
        return False

    @dbus.service.signal(DBUSMENU_INTERFACE, signature="ui")
    def LayoutUpdated(self, revision: int, parent: int):
        pass


class MbVpnTrayItem(dbus.service.Object):
    def __init__(
        self,
        bus: dbus.SessionBus,
        on_activate: Optional[Callable[[], None]] = None,
        on_toggle_vpn: Optional[Callable[[], None]] = None,
        on_connect_target: Optional[Callable[[str, str, str, str], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
        get_recent_servers: Optional[Callable[[], List[Dict[str, str]]]] = None,
    ):
        self.bus = bus
        self.on_activate_cb = on_activate
        self.on_toggle_vpn_cb = on_toggle_vpn
        self.on_connect_target_cb = on_connect_target
        self.on_quit_cb = on_quit
        self.get_recent_servers_cb = get_recent_servers

        self.service_name = f"org.kde.StatusNotifierItem-{os.getpid()}-1"
        self.bus_name = dbus.service.BusName(self.service_name, bus=self.bus)
        super().__init__(self.bus_name, "/StatusNotifierItem")

        self.dbus_menu = DbusMenu(self.bus_name, "/MenuBar")

        self._connected = False
        self._server = ""
        self._icon_name = "security-low-symbolic"
        self._title = "MalwarebytesVPN"
        self._tooltip_sub = "Encrypted tunnel inactive"

        self._rebuild_menu()
        self._register_with_watcher()

    def _register_with_watcher(self):
        try:
            watcher = self.bus.get_object("org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher")
            watcher.RegisterStatusNotifierItem(
                "/StatusNotifierItem",
                dbus_interface="org.kde.StatusNotifierWatcher"
            )
            print("[Tray] Successfully registered with StatusNotifierWatcher")
        except Exception as e:
            print("[Tray] Could not register with StatusNotifierWatcher:", e)

    def _rebuild_menu(self):
        menu_items = []

        # 1. Status Row (Header)
        status_text = f"Protected ({self._server})" if self._connected else "Unprotected (Tunnel Inactive)"
        menu_items.append({
            "id": 1,
            "label": f"🛡️  {status_text}",
            "enabled": False,
        })
        menu_items.append({"id": 2, "type": "separator"})

        # 2. Fastest Location Option
        def select_fastest():
            if self.on_connect_target_cb:
                self.on_connect_target_cb("us", "Fastest Server (Auto)", "⚡", "Optimal Latency Routing")

        menu_items.append({
            "id": 10,
            "label": "⚡  Fastest Location (Auto)",
            "enabled": True,
            "action": select_fastest,
        })

        # 3. Recent Servers List
        recent = self.get_recent_servers_cb() if self.get_recent_servers_cb else []
        if recent:
            menu_items.append({"id": 20, "type": "separator"})
            menu_items.append({
                "id": 21,
                "label": "Recent Locations:",
                "enabled": False,
            })
            for idx, r in enumerate(recent[:4]):
                srv_id = 30 + idx
                target = r.get("target", "us")
                label = r.get("label", target)
                flag = r.get("flag", "🌐")
                sub = r.get("sub", "")

                def make_connect(t=target, l=label, f=flag, s=sub):
                    return lambda: self.on_connect_target_cb(t, l, f, s) if self.on_connect_target_cb else None

                menu_items.append({
                    "id": srv_id,
                    "label": f"  {flag}  {label}",
                    "enabled": True,
                    "action": make_connect(),
                })

        # 4. Action separator
        menu_items.append({"id": 50, "type": "separator"})

        # 5. Connect / Disconnect Toggle
        toggle_label = "Disconnect from VPN" if self._connected else "Connect to VPN"
        menu_items.append({
            "id": 51,
            "label": f"🔄  {toggle_label}",
            "enabled": True,
            "action": self.on_toggle_vpn_cb,
        })

        # 6. Open Dashboard
        menu_items.append({
            "id": 52,
            "label": "🖥️  Open Dashboard",
            "enabled": True,
            "action": self.on_activate_cb,
        })

        # 7. Quit Separator
        menu_items.append({"id": 90, "type": "separator"})

        # 8. Quit Button
        menu_items.append({
            "id": 99,
            "label": "❌  Quit Malwarebytes VPN",
            "enabled": True,
            "action": self.on_quit_cb,
        })

        self.dbus_menu.set_menu_structure(menu_items)

    def update_status(self, connected: bool, server: Optional[str] = None):
        changed = (self._connected != connected or self._server != (server or ""))
        self._connected = connected
        self._server = server or ""

        if connected:
            self._icon_name = "security-high-symbolic"
            self._tooltip_sub = f"Protected via {self._server or 'WireGuard'}"
        else:
            self._icon_name = "security-low-symbolic"
            self._tooltip_sub = "Encrypted tunnel inactive"

        self._rebuild_menu()

        if changed:
            self.NewIcon()
            self.NewToolTip()
            self.NewStatus("Active" if connected else "Passive")

    # --- org.kde.StatusNotifierItem DBus Methods ---

    @dbus.service.method(SNI_INTERFACE, in_signature="ii", out_signature="")
    def Activate(self, x: int, y: int):
        if self.on_activate_cb:
            GLib.idle_add(self.on_activate_cb)

    @dbus.service.method(SNI_INTERFACE, in_signature="ii", out_signature="")
    def SecondaryActivate(self, x: int, y: int):
        if self.on_toggle_vpn_cb:
            GLib.idle_add(self.on_toggle_vpn_cb)

    @dbus.service.method(SNI_INTERFACE, in_signature="ii", out_signature="")
    def ContextMenu(self, x: int, y: int):
        pass

    @dbus.service.method(SNI_INTERFACE, in_signature="is", out_signature="")
    def Scroll(self, delta: int, orientation: str):
        pass

    # --- DBus Signals ---

    @dbus.service.signal(SNI_INTERFACE)
    def NewTitle(self):
        pass

    @dbus.service.signal(SNI_INTERFACE)
    def NewIcon(self):
        pass

    @dbus.service.signal(SNI_INTERFACE)
    def NewAttentionIcon(self):
        pass

    @dbus.service.signal(SNI_INTERFACE)
    def NewOverlayIcon(self):
        pass

    @dbus.service.signal(SNI_INTERFACE)
    def NewToolTip(self):
        pass

    @dbus.service.signal(SNI_INTERFACE, signature="s")
    def NewStatus(self, status: str):
        pass

    # --- Properties ---

    @dbus.service.method(PROPERTIES_INTERFACE, in_signature="ss", out_signature="v")
    def Get(self, interface_name: str, property_name: str):
        props = self.GetAll(interface_name)
        if property_name in props:
            return props[property_name]
        raise dbus.exceptions.DBusException(
            f"Unknown property {property_name}",
            name="org.freedesktop.DBus.Error.UnknownProperty"
        )

    @dbus.service.method(PROPERTIES_INTERFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface_name: str):
        if interface_name != SNI_INTERFACE:
            return {}

        return {
            "Category": dbus.String("ApplicationStatus"),
            "Id": dbus.String("mbvpn"),
            "Title": dbus.String(self._title),
            "Status": dbus.String("Active" if self._connected else "Passive"),
            "WindowId": dbus.UInt32(0),
            "IconThemePath": dbus.String(os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps")),
            "IconName": dbus.String(self._icon_name),
            "IconPixmap": dbus.Array([], signature="(iiiay)"),
            "OverlayIconName": dbus.String(""),
            "OverlayIconPixmap": dbus.Array([], signature="(iiiay)"),
            "AttentionIconName": dbus.String(""),
            "AttentionIconPixmap": dbus.Array([], signature="(iiiay)"),
            "AttentionMovieName": dbus.String(""),
            "ToolTip": dbus.Struct(
                (
                    dbus.String(self._icon_name),
                    dbus.Array([], signature="(iiay)"),
                    dbus.String(self._title),
                    dbus.String(self._tooltip_sub),
                ),
                signature="sa(iiay)ss"
            ),
            "ItemIsMenu": dbus.Boolean(True),
            "Menu": dbus.ObjectPath("/MenuBar"),
        }


_tray_instance: Optional[MbVpnTrayItem] = None


def init_tray(
    on_activate: Optional[Callable[[], None]] = None,
    on_toggle_vpn: Optional[Callable[[], None]] = None,
    on_connect_target: Optional[Callable[[str, str, str, str], None]] = None,
    on_quit: Optional[Callable[[], None]] = None,
    get_recent_servers: Optional[Callable[[], List[Dict[str, str]]]] = None,
) -> Optional[MbVpnTrayItem]:
    global _tray_instance
    if _tray_instance is not None:
        _tray_instance.on_activate_cb = on_activate
        _tray_instance.on_toggle_vpn_cb = on_toggle_vpn
        _tray_instance.on_connect_target_cb = on_connect_target
        _tray_instance.on_quit_cb = on_quit
        _tray_instance.get_recent_servers_cb = get_recent_servers
        _tray_instance._rebuild_menu()
        return _tray_instance

    try:
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
        _tray_instance = MbVpnTrayItem(
            bus=bus,
            on_activate=on_activate,
            on_toggle_vpn=on_toggle_vpn,
            on_connect_target=on_connect_target,
            on_quit=on_quit,
            get_recent_servers=get_recent_servers,
        )
        return _tray_instance
    except Exception as e:
        print("[Tray] Failed to initialize D-Bus tray:", e)
        return None
