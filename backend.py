#!/usr/bin/env python3
"""
Backend interface for Malwarebytes Privacy VPN (mbvpn CLI) on Linux.
Provides clean async/threaded-safe API for GUI interactions, rich telemetry,
automatic license key exchange, and full server discovery.
"""

import json
import os
import re
import shutil
import socket
import subprocess
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def country_code_to_flag(code: str) -> str:
    """Converts a two-letter ISO country code to an emoji flag."""
    code = code.strip().upper()
    if len(code) == 2 and code.isalpha():
        return "".join(chr(ord(c) + 127397) for c in code)
    return "🌐"


@dataclass
class ConnectionStatus:
    connected: bool = False
    server: Optional[str] = None
    endpoint: Optional[str] = None
    handshake: Optional[str] = None
    transfer_down: Optional[str] = None
    transfer_up: Optional[str] = None
    ip: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    raw_output: str = ""


@dataclass
class ServerItem:
    hostname: str
    ipv4: str
    weight: int = 0


@dataclass
class CityItem:
    name: str
    code: str
    un_locode: str
    country_code: str
    country_name: str
    servers: List[ServerItem] = field(default_factory=list)


@dataclass
class CountryItem:
    name: str
    code: str
    flag: str
    default_city: str
    cities: List[CityItem] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    streaming_tag: str = ""
    torrenting_tag: str = ""
    privacy_tag: str = ""
    fastest_tag: str = ""
    region: str = ""


COUNTRY_REGIONS = {
    # Europe & United Kingdom (21)
    "gb": "Europe & United Kingdom",
    "de": "Europe & United Kingdom",
    "fr": "Europe & United Kingdom",
    "at": "Europe & United Kingdom",
    "be": "Europe & United Kingdom",
    "cz": "Europe & United Kingdom",
    "dk": "Europe & United Kingdom",
    "ee": "Europe & United Kingdom",
    "fi": "Europe & United Kingdom",
    "gr": "Europe & United Kingdom",
    "ie": "Europe & United Kingdom",
    "it": "Europe & United Kingdom",
    "nl": "Europe & United Kingdom",
    "no": "Europe & United Kingdom",
    "pl": "Europe & United Kingdom",
    "pt": "Europe & United Kingdom",
    "ro": "Europe & United Kingdom",
    "es": "Europe & United Kingdom",
    "se": "Europe & United Kingdom",
    "ch": "Europe & United Kingdom",
    "ua": "Europe & United Kingdom",
    # North & Central America (3)
    "us": "North & Central America",
    "ca": "North & Central America",
    "mx": "North & Central America",
    # Asia-Pacific & Oceania (7)
    "au": "Asia-Pacific & Oceania",
    "nz": "Asia-Pacific & Oceania",
    "jp": "Asia-Pacific & Oceania",
    "sg": "Asia-Pacific & Oceania",
    "hk": "Asia-Pacific & Oceania",
    "id": "Asia-Pacific & Oceania",
    "th": "Asia-Pacific & Oceania",
    # South America, Middle East & Africa (5)
    "ar": "South America, Middle East & Africa",
    "cl": "South America, Middle East & Africa",
    "co": "South America, Middle East & Africa",
    "il": "South America, Middle East & Africa",
    "za": "South America, Middle East & Africa",
}


SERVER_CATEGORIES = {
    "all": {
        "label": "All",
        "title": "All Locations",
        "subtitle": "62 Locations Worldwide • 150+ Physical RAM Servers",
    },
    "streaming": {
        "label": "Streaming",
        "title": "Streaming Optimized",
        "subtitle": "Netflix, Hulu, BBC iPlayer, Prime & Disney+",
        "countries": ["us", "gb", "ca", "jp", "de", "fr", "au", "it", "es"],
        "tags": {
            "us": "Netflix US, Hulu, HBO Max, Disney+, Peacock",
            "gb": "BBC iPlayer, ITVX, Channel 4, Sky Go",
            "ca": "Netflix CA, Crave, CBC Gem, TSN",
            "jp": "Netflix JP, ABEMA, U-NEXT, TVer",
            "de": "ZDF, ARD Mediathek, Joyn, WOW",
            "fr": "Canal+, France TV, Molotov, 6play",
            "au": "Stan, ABC iview, 10 Play, 9Now",
            "it": "RaiPlay, Mediaset Infinity, DAZN IT",
            "es": "RTVE Play, Movistar+, ATRESplayer",
        },
    },
    "torrenting": {
        "label": "Torrenting",
        "title": "P2P / BitTorrent",
        "subtitle": "High-Throughput Swarms & Privacy Jurisdictions",
        "countries": ["ch", "nl", "se", "es", "ro", "no", "cz", "pl", "mx"],
        "tags": {
            "ch": "Swiss Privacy Law • Zero Logging • Safe P2P",
            "nl": "10Gbps AMS-IX Transit • Fast Swarms",
            "se": "Nordic Privacy • High-Bandwidth BitTorrent",
            "ro": "Constitutional Privacy • No EU Retention",
            "es": "High-Throughput P2P • No Mandatory Logs",
            "no": "Nordic Privacy Backbone • Tier-1 Transit",
            "cz": "Central European High-Speed P2P Node",
            "pl": "Robust Eastern European Torrent Routing",
            "mx": "Latin American High-Throughput Node",
        },
    },
    "fastest": {
        "label": "Fastest",
        "title": "Lowest Latency",
        "subtitle": "Direct Tier-1 Internet Exchange Points",
        "countries": ["sg", "hk", "jp", "de", "nl", "gb", "us"],
        "tags": {
            "sg": "Asia-Pacific Equinix Fiber Hub",
            "hk": "Submarine Cable Gateway • Low Latency",
            "jp": "Pacific Rim High-Speed Transit",
            "de": "DE-CIX Frankfurt Exchange Node",
            "nl": "AMS-IX Amsterdam Exchange Node",
            "gb": "LINX London Internet Exchange Node",
            "us": "North American Transcontinental Backbone",
        },
    },
    "privacy": {
        "label": "Privacy",
        "title": "Non-14-Eyes & Offshore",
        "subtitle": "Outside 14-Eyes Surveillance Alliances",
        "countries": ["ch", "ro", "es", "mx", "co", "id", "za"],
        "tags": {
            "ch": "Non-EU / Non-14-Eyes • Swiss Secrecy Laws",
            "ro": "Non-14-Eyes • Anti-Surveillance Constitution",
            "mx": "Non-14-Eyes • Offshore Jurisdiction",
            "co": "Non-14-Eyes • Latin American Privacy",
            "id": "Non-14-Eyes • Southeast Asia",
            "za": "Non-14-Eyes • African Backbone",
            "es": "Strict Constitutional Protection",
        },
    },
}


class ProtonKillSwitch:
    SERVICE = "me.proton.vpn.kill_switch"
    PATH = "/me/proton/vpn/kill_switch"

    @classmethod
    def is_available(cls) -> bool:
        return os.path.exists("/usr/share/dbus-1/system-services/me.proton.vpn.kill_switch.service")

    @classmethod
    def enable(cls, server_ip: str = "") -> Tuple[bool, str]:
        cmd = [
            "busctl", "call",
            cls.SERVICE,
            cls.PATH,
            cls.SERVICE,
            "Enable",
            "(ussb)",
            "0",
            "",
            server_ip or "",
            "false",
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)
            if res.returncode == 0:
                return True, "Kill switch enabled via ProtonVPN engine"
            return False, res.stderr.strip() or "Failed to call ProtonVPN kill switch"
        except Exception as e:
            return False, str(e)

    @classmethod
    def disable(cls) -> Tuple[bool, str]:
        cmd = [
            "busctl", "call",
            cls.SERVICE,
            cls.PATH,
            cls.SERVICE,
            "Disable",
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)
            if res.returncode == 0:
                return True, "Kill switch disabled via ProtonVPN engine"
            return False, res.stderr.strip() or "Failed to disable ProtonVPN kill switch"
        except Exception as e:
            return False, str(e)


class ProtonSplitTunneling:
    SERVICE = "me.proton.vpn.split_tunneling"
    PATH = "/me/proton/vpn/split_tunneling"

    @classmethod
    def is_available(cls) -> bool:
        return os.path.exists("/usr/share/dbus-1/system-services/me.proton.vpn.split_tunneling.service")

    @classmethod
    def apply_bypass_config(cls, app_paths: List[str], ip_ranges: Optional[List[str]] = None) -> bool:
        try:
            import asyncio
            from dbus_fast import BusType, Variant
            from dbus_fast.aio import MessageBus

            async def _run():
                bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
                introspection = await bus.introspect(cls.SERVICE, cls.PATH)
                proxy = bus.get_proxy_object(cls.SERVICE, cls.PATH, introspection)
                iface = proxy.get_interface(cls.SERVICE)

                paths = [p for p in set(app_paths) if p and os.path.exists(p)]
                ranges = ip_ranges or []

                config = {
                    "mode": Variant("s", "exclude"),
                    "app_paths": Variant("as", paths),
                    "ip_ranges": Variant("as", ranges),
                }
                await iface.call_set_config(1000, config)
                bus.disconnect()
                return True

            return asyncio.run(_run())
        except Exception as e:
            print("Error configuring split tunneling:", e)
            return False


class MbVpnBackend:
    def __init__(self, binary_path: Optional[str] = None, firewall_path: Optional[str] = None):
        self.binary_path = binary_path or self._find_binary()
        self.firewall_path = firewall_path or self._find_firewall_binary()
        self.config_dir = Path.home() / ".config" / "mbvpn"
        self._servers_cache: Optional[List[CountryItem]] = None
        self._killswitch_active: bool = False
        self._active_vpn_interface: Optional[str] = None
        self._lock = threading.Lock()

    def apply_split_tunneling(self, app_paths: List[str], ip_ranges: Optional[List[str]] = None) -> bool:
        """Applies application split tunneling / bypass using Proton's eBPF daemon."""
        if ProtonSplitTunneling.is_available():
            return ProtonSplitTunneling.apply_bypass_config(app_paths, ip_ranges)
        return False

    def resolve_website_ips(self, target: str) -> List[str]:
        """
        Resolves domain names, hostnames, URLs or IPs into a list of IPv4 addresses.
        Supports CIDR subnets (e.g. '192.168.1.0/24').
        """
        target = target.strip()
        if not target:
            return []
        if "://" in target:
            target = target.split("://", 1)[1]
        target = target.split("/")[0].split("?")[0].split("#")[0].strip()
        if ":" in target:
            parts = target.split(":")
            if len(parts) == 2 and parts[1].isdigit():
                target = parts[0]
        ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$"
        if re.match(ip_pattern, target):
            return [target]
        ips = []
        try:
            addr_info = socket.getaddrinfo(target, None, socket.AF_INET, socket.SOCK_STREAM)
            for item in addr_info:
                ip = item[4][0]
                if ip not in ips:
                    ips.append(ip)
        except Exception:
            try:
                ip = socket.gethostbyname(target)
                if ip and ip not in ips:
                    ips.append(ip)
            except Exception:
                pass
        return ips

    def get_bypassed_website_ips(self, websites: List[str]) -> List[str]:
        """Resolves a list of websites or domains into a unique list of IP addresses."""
        all_ips = []
        for site in websites:
            for ip in self.resolve_website_ips(site):
                if ip not in all_ips:
                    all_ips.append(ip)
        return all_ips

    def apply_website_split_tunneling(self, websites: List[str], enabled: bool = True) -> Tuple[bool, str]:
        """
        Routes traffic for the specified websites / IPs directly via the local physical interface,
        bypassing the WireGuard VPN tunnel.
        """
        if not self.is_firewall_available():
            return False, "Firewall helper not available"

        # Always flush previous split-tunnel routes first
        self.clear_website_split_tunneling()

        if not enabled or not websites:
            return True, "Split tunneling inactive"

        ips_to_bypass = self.get_bypassed_website_ips(websites)
        if not ips_to_bypass:
            return False, "No valid IP addresses could be resolved for the specified websites"

        added_count = 0
        for ip in ips_to_bypass:
            try:
                res = subprocess.run([self.firewall_path, "route-add", ip], capture_output=True, text=True, timeout=3, check=False)
                if res.returncode == 0:
                    added_count += 1
            except Exception:
                pass

        return True, f"Bypassed {added_count} IP(s) for {len(websites)} website(s)"

    def clear_website_split_tunneling(self) -> bool:
        """Removes all split-tunnel routes (proto 77) from the routing table."""
        if not self.is_firewall_available():
            return False
        try:
            res = subprocess.run([self.firewall_path, "route-flush"], capture_output=True, text=True, timeout=4, check=False)
            return res.returncode == 0
        except Exception:
            return False

    def get_active_split_tunnel_routes(self) -> List[str]:
        """Returns the list of active split-tunnel routes configured in kernel."""
        try:
            res = subprocess.run(["ip", "-4", "route", "show", "proto", "77"], capture_output=True, text=True, timeout=2, check=False)
            return [line.strip() for line in res.stdout.splitlines() if line.strip()]
        except Exception:
            return []

    def _find_binary(self) -> str:
        candidates = [
            os.path.expanduser("~/.local/bin/mbvpn"),
            "/usr/local/bin/mbvpn",
            "/usr/bin/mbvpn",
            shutil.which("mbvpn"),
        ]
        for c in candidates:
            if c and os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        return "mbvpn"

    def _find_firewall_binary(self) -> str:
        candidates = [
            os.path.expanduser("~/.local/bin/mbvpn-firewall"),
            "/usr/local/bin/mbvpn-firewall",
            "/usr/bin/mbvpn-firewall",
            shutil.which("mbvpn-firewall"),
        ]
        for c in candidates:
            if c and os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        return os.path.expanduser("~/.local/bin/mbvpn-firewall")

    def is_binary_available(self) -> bool:
        if os.path.isabs(self.binary_path):
            return os.path.isfile(self.binary_path) and os.access(self.binary_path, os.X_OK)
        return shutil.which(self.binary_path) is not None

    def is_firewall_available(self) -> bool:
        if os.path.isabs(self.firewall_path):
            return os.path.isfile(self.firewall_path) and os.access(self.firewall_path, os.X_OK)
        return shutil.which(self.firewall_path) is not None

    def has_firewall_capabilities(self) -> bool:
        if not self.is_firewall_available():
            return False
        real_fw = os.path.realpath(self.firewall_path)
        try:
            res = subprocess.run(
                ["getcap", real_fw],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            return "cap_net_admin" in res.stdout
        except Exception:
            return False

    def check_capabilities(self) -> Tuple[bool, str]:
        if not self.is_binary_available():
            return False, "mbvpn binary not found"
        real_path = os.path.realpath(self.binary_path)
        try:
            res = subprocess.run(
                ["getcap", real_path],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            output = res.stdout.strip()
            if "cap_net_admin" not in output:
                return False, "mbvpn missing cap_net_admin capability"
        except FileNotFoundError:
            return False, "getcap tool not available"

        # Check firewall binary capabilities as well
        if self.is_firewall_available():
            real_fw = os.path.realpath(self.firewall_path)
            try:
                res = subprocess.run(
                    ["getcap", real_fw],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
                output = res.stdout.strip()
                if "cap_net_admin" not in output:
                    return False, "mbvpn-firewall missing cap_net_admin capability"
            except Exception:
                pass

        return True, "All network capabilities configured"

    def is_logged_in(self) -> bool:
        config_file = self.config_dir / "config.yml"
        if not config_file.exists():
            return False
        try:
            content = config_file.read_text(encoding="utf-8")
            match = re.search(r'installation_token:\s*["\']?([^"\'\s]+)["\']?', content)
            return bool(match and match.group(1).strip())
        except Exception:
            return False

    def _run_cmd(self, args: List[str], timeout: int = 15) -> Tuple[int, str, str]:
        if not self.is_binary_available():
            return 127, "", "mbvpn binary not found"
        cmd = [self.binary_path] + args
        with self._lock:
            try:
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                return res.returncode, res.stdout, res.stderr
            except subprocess.TimeoutExpired:
                return -1, "", f"Command '{' '.join(args)}' timed out after {timeout}s"
            except Exception as e:
                return -2, "", str(e)

    @staticmethod
    def _format_bytes(num_bytes: int) -> str:
        """Formats byte count to human-readable string (KB, MB, GB)."""
        val = float(num_bytes)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if val < 1024.0:
                return f"{val:.1f} {unit}"
            val /= 1024.0
        return f"{val:.1f} PB"

    def _get_client_credentials(self) -> Tuple[str, str, str]:
        """
        Retrieves (private_key, ipv4, ipv6) from config.yml and account_info.json.
        """
        privkey = ""
        config_file = self.config_dir / "config.yml"
        if config_file.exists():
            try:
                content = config_file.read_text(encoding="utf-8")
                m = re.search(r'private_key:\s*["\']?([^"\'\s]+)["\']?', content)
                if m:
                    privkey = m.group(1).strip()
            except Exception:
                pass

        ipv4 = "10.5.122.222"
        ipv6 = ""
        acc_file = self.config_dir / "account_info.json"
        if acc_file.exists():
            try:
                with open(acc_file, "r", encoding="utf-8") as f:
                    acc_data = json.load(f)
                    ipv4 = acc_data.get("ipv4") or ipv4
                    ipv6 = acc_data.get("ipv6") or ""
            except Exception:
                pass

        return privkey, ipv4, ipv6

    def _resolve_server(self, target: str) -> Optional[Dict[str, Any]]:
        """
        Resolves any target string (server hostname, country code, city code, or name)
        into a complete server specification from servers.json.
        """
        target = (target or "").strip()
        if not target or target.lower() in ("auto", "fastest"):
            target = "sg"

        target_l = target.lower()
        servers_file = self.config_dir / "servers.json"
        if not servers_file.exists():
            bundled = Path(__file__).parent / "assets" / "servers.json"
            if bundled.exists():
                servers_file = bundled
            else:
                self._run_cmd(["servers"], timeout=10)
        if not servers_file.exists():
            return None

        try:
            with open(servers_file, "r", encoding="utf-8") as f:
                servers_data = json.load(f)

            items = []
            for c in servers_data.get("countries", []):
                c_code = c.get("code", "").lower()
                c_name = c.get("name", "")
                for city in c.get("cities", []):
                    ct_code = city.get("code", "").lower()
                    ct_name = city.get("name", "")
                    un_locode = city.get("unLocode", "").lower()
                    for s in city.get("servers", []):
                        h = s.get("hostname", "")
                        prefix = h.split(".")[0].lower()
                        items.append({
                            "server": s,
                            "hostname": h,
                            "prefix": prefix,
                            "country_code": c_code,
                            "country_name": c_name,
                            "city_code": ct_code,
                            "city_name": ct_name,
                            "un_locode": un_locode,
                        })

            if not items:
                return None

            # 1. Exact match on prefix or full hostname
            for it in items:
                if target_l == it["prefix"] or target_l == it["hostname"].lower():
                    return it

            # 2. Exact match on country code (e.g. "us", "sg", "de")
            for it in items:
                if target_l == it["country_code"]:
                    return it

            # 3. Exact match on city code or un_locode (e.g. "sea", "fra", "sin")
            for it in items:
                if target_l == it["city_code"] or target_l == it["un_locode"]:
                    return it

            # 4. Exact match on country name (e.g. "United States", "Germany")
            for it in items:
                if target_l == it["country_name"].lower():
                    return it

            # 5. Prefix starts with target (e.g. "us-sea", "de-fra")
            for it in items:
                if it["prefix"].startswith(target_l):
                    return it

            # 6. Target in country or city name
            for it in items:
                if target_l in it["country_name"].lower() or target_l in it["city_name"].lower():
                    return it

            return items[0]
        except Exception:
            return None

    def _connect_networkmanager(self, target: str, progress_callback=None, srv_info=None) -> Tuple[bool, str]:
        """
        Connects via NetworkManager WireGuard connection profile.
        - Sets native Malwarebytes gateway DNS (10.0.0.1) directly on the interface.
        - Sets catch-all search domain '~.' and priority -50.
        - Zero password prompts (Polkit allow_active=yes for network-control).
        - 100% leak-free DNS resolution.
        - srv_info: pass pre-resolved server dict to avoid double _resolve_server call.
        """
        privkey, client_ipv4, client_ipv6 = self._get_client_credentials()
        if not privkey:
            return False, "WireGuard private key missing in config.yml"

        if srv_info is None:
            srv_info = self._resolve_server(target)
        if not srv_info:
            return False, f"Could not find a valid server for '{target}'"

        srv = srv_info["server"]
        peer_pubkey = srv.get("publicKey")
        peer_ip = srv.get("ipv4AddrIn")
        peer_port = 51820
        dns_gateway = srv.get("ipv4Gateway", "10.0.0.1")

        if not peer_pubkey or not peer_ip:
            return False, f"Server {srv_info['hostname']} missing WireGuard public key or IP"

        def report(message: str):
            if progress_callback:
                progress_callback(message)

        # 1. Add WireGuard connection profile
        add_cmd = [
            "nmcli", "connection", "add",
            "type", "wireguard",
            "con-name", "mbvpn",
            "ifname", "wg-mbvpn",
            "autoconnect", "no",
            "ipv4.method", "manual",
            "ipv4.addresses", f"{client_ipv4}/32",
            "ipv4.dns", dns_gateway,
            "ipv4.dns-search", "~.",
            "ipv4.dns-priority", "-50",
            "ipv6.method", "disabled",
            "wireguard.private-key", privkey,
            "wireguard.listen-port", "51820",
        ]
        report("Creating the WireGuard profile…")
        res = subprocess.run(add_cmd, capture_output=True, text=True, timeout=8, check=False)
        if res.returncode != 0:
            return False, f"Failed to create WireGuard profile: {res.stderr.strip()}"

        # 2. Configure peer with 24/7 persistent keepalive (prevents NAT router state drops)
        peer_spec = f"{peer_pubkey} endpoint={peer_ip}:{peer_port} allowed-ips=0.0.0.0/0 persistent-keepalive=25"
        peer_cmd = [
            "nmcli", "connection", "modify", "mbvpn",
            "wireguard.peers", peer_spec,
        ]
        report("Configuring the VPN server…")
        res_peer = subprocess.run(peer_cmd, capture_output=True, text=True, timeout=8, check=False)
        if res_peer.returncode != 0:
            self._disconnect_networkmanager()
            return False, f"Failed to configure WireGuard peer: {res_peer.stderr.strip()}"

        # 3. Bring up connection
        up_cmd = ["nmcli", "connection", "up", "mbvpn"]
        report("Waiting for NetworkManager to bring up WireGuard…")
        res_up = subprocess.run(up_cmd, capture_output=True, text=True, timeout=12, check=False)
        if res_up.returncode != 0:
            self._disconnect_networkmanager()
            return False, f"Failed to activate WireGuard connection: {res_up.stderr.strip()}"

        # 4. Store active session metadata
        import time
        session_data = {
            "server": srv_info["hostname"],
            "prefix": srv_info["prefix"],
            "country": srv_info["country_name"],
            "city": srv_info["city_name"],
            "country_code": srv_info["country_code"],
            "endpoint": f"{peer_ip}:{peer_port}",
            "ip": peer_ip,
            "client_ip": client_ipv4,
            "dns": dns_gateway,
            "connected_at": time.time(),
        }
        try:
            with open(self.config_dir / "active_session.json", "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2)
        except Exception:
            pass

        self._active_vpn_interface = "wg-mbvpn"
        return True, f"Connected to {srv_info['prefix']} ({srv_info['city_name']}, {srv_info['country_name']})"

    def _disconnect_networkmanager(self) -> Tuple[bool, str]:
        """Tears down and deletes the NetworkManager WireGuard connection profile."""
        try:
            # Run 'down' and wait briefly, then 'delete' — keep timeouts short since
            # we don't need to block on full teardown confirmation.
            subprocess.run(["nmcli", "connection", "down", "mbvpn"], capture_output=True, timeout=4, check=False)
            subprocess.run(["nmcli", "connection", "delete", "mbvpn"], capture_output=True, timeout=3, check=False)
        except Exception:
            pass

        session_file = self.config_dir / "active_session.json"
        try:
            session_file.unlink(missing_ok=True)
        except Exception:
            pass

        self._active_vpn_interface = None
        return True, "Disconnected successfully"

    def get_status(self) -> ConnectionStatus:
        # 1. First check if NetworkManager WireGuard session is active
        session_file = self.config_dir / "active_session.json"
        is_nm_active = False
        try:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,STATE", "connection", "show", "--active"],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            if res.returncode == 0:
                for line in res.stdout.strip().splitlines():
                    if line.startswith("mbvpn:") or line.startswith("wg-mbvpn:"):
                        is_nm_active = True
                        break
        except Exception:
            pass

        if not is_nm_active and os.path.exists("/sys/class/net/wg-mbvpn"):
            is_nm_active = True

        if is_nm_active:
            status = ConnectionStatus(connected=True)
            sess = {}
            if session_file.exists():
                try:
                    with open(session_file, "r", encoding="utf-8") as f:
                        sess = json.load(f)
                except Exception:
                    pass

            status.server = sess.get("prefix") or sess.get("server") or "wg-mbvpn"
            status.endpoint = sess.get("endpoint")
            status.ip = sess.get("ip") or sess.get("client_ip")
            status.country = sess.get("country")
            status.country_code = sess.get("country_code")
            status.city = sess.get("city")
            status.handshake = "Active"

            # Parse transfer statistics from ip -s link show wg-mbvpn
            try:
                ip_res = subprocess.run(
                    ["ip", "-s", "link", "show", "dev", "wg-mbvpn"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
                if ip_res.returncode == 0:
                    lines = ip_res.stdout.splitlines()
                    for idx, line in enumerate(lines):
                        if "RX:" in line and idx + 1 < len(lines):
                            rx_parts = lines[idx + 1].strip().split()
                            if rx_parts:
                                rx_bytes = int(rx_parts[0])
                                status.transfer_down = self._format_bytes(rx_bytes)
                        if "TX:" in line and idx + 1 < len(lines):
                            tx_parts = lines[idx + 1].strip().split()
                            if tx_parts:
                                tx_bytes = int(tx_parts[0])
                                status.transfer_up = self._format_bytes(tx_bytes)
            except Exception:
                pass

            return status

        # 2. Fallback to CLI status check if mbvpn-linux binary was used
        code, stdout, stderr = self._run_cmd(["status"], timeout=8)
        text = stdout + "\n" + stderr
        status = ConnectionStatus(raw_output=text.strip())

        connected_match = re.search(r"(?:Connected to:|Connected to)\s*([^\r\n]+)", text, re.IGNORECASE)
        if connected_match:
            status.connected = True
            status.server = connected_match.group(1).strip()
        elif "No active connections" in text or "no active session" in text.lower():
            status.connected = False

        endpoint_match = re.search(r"Endpoint:\s*([^\r\n]+)", text)
        if endpoint_match:
            status.endpoint = endpoint_match.group(1).strip()

        handshake_match = re.search(r"Last handshake:\s*([^\r\n]+)", text)
        if handshake_match:
            status.handshake = handshake_match.group(1).strip()

        transfer_match = re.search(r"Transfer:\s*↓\s*([0-9\.]+\s*[KMGTPE]?B)\s*/\s*↑\s*([0-9\.]+\s*[KMGTPE]?B)", text)
        if transfer_match:
            status.transfer_down = transfer_match.group(1).strip()
            status.transfer_up = transfer_match.group(2).strip()

        ip_match = re.search(r"IP Address:\s*([0-9a-fA-F\.:]+)", text)
        if ip_match:
            status.ip = ip_match.group(1).strip()

        country_match = re.search(r"Country:\s*([^\r\n]*)", text)
        if country_match:
            val = country_match.group(1).strip()
            if val:
                status.country = val

        city_match = re.search(r"City:\s*([^\r\n]*)", text)
        if city_match:
            val = city_match.group(1).strip()
            if val:
                status.city = val

        return status

    def _get_active_physical_interfaces(self) -> List[str]:
        """Returns active physical WiFi/Ethernet network interfaces managed by NetworkManager."""
        try:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "dev"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            devices = []
            for line in res.stdout.strip().splitlines():
                parts = line.split(":")
                if len(parts) >= 3:
                    dev, dev_type, state = parts[0], parts[1], parts[2]
                    if state == "connected" and dev_type in ("wifi", "ethernet"):
                        devices.append(dev)
            return devices or ["wlp2s0"]
        except Exception:
            return ["wlp2s0"]

    def get_active_vpn_interface(self) -> Optional[str]:
        """
        Discovers the active WireGuard VPN network interface on any Linux distribution.
        1. Checks kernel routing table for the 0.0.0.0/1 VPN default gateway route.
        2. Checks active wireguard type interfaces via ip link.
        3. Checks interface matching the currently connected server identifier.
        """
        # 1. Routing table inspection (fast, universal, accurate)
        try:
            res = subprocess.run(
                ["ip", "-4", "route", "show", "0.0.0.0/1"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if res.returncode == 0 and res.stdout:
                parts = res.stdout.strip().split()
                if "dev" in parts:
                    idx = parts.index("dev")
                    if idx + 1 < len(parts):
                        dev = parts[idx + 1].strip()
                        if dev:
                            self._active_vpn_interface = dev
                            return dev
        except Exception:
            pass

        # 2. WireGuard link type inspection
        try:
            res = subprocess.run(
                ["ip", "-br", "link", "show", "type", "wireguard"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.strip().splitlines():
                    parts = line.split()
                    if parts:
                        dev = parts[0].strip()
                        if dev:
                            self._active_vpn_interface = dev
                            return dev
        except Exception:
            pass

        # 3. Server name status fallback
        try:
            status = self.get_status()
            if status.connected and status.server:
                srv = status.server.strip()
                if os.path.exists(f"/sys/class/net/{srv}"):
                    self._active_vpn_interface = srv
                    return srv
        except Exception:
            pass

        return self._active_vpn_interface

    def _get_active_physical_connections(self) -> List[Tuple[str, str]]:
        """Returns list of (connection_name, device_name) for active wifi and ethernet connections."""
        results = []
        try:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            for line in res.stdout.strip().splitlines():
                parts = line.split(":")
                if len(parts) >= 3:
                    name, c_type, dev = parts[0], parts[1], parts[2]
                    if c_type in ("802-11-wireless", "wifi", "802-3-ethernet", "ethernet"):
                        results.append((name, dev))
        except Exception:
            pass
        return results

    def enable_dns_protection(self, vpn_interface: Optional[str] = None) -> bool:
        """
        Prevents DNS leaks completely and passwordlessly:
        If NetworkManager manages the tunnel interface, DNS is already set natively.
        Otherwise configures systemd-resolved using --no-ask-password.
        """
        import time
        iface = vpn_interface or self.get_active_vpn_interface()
        if not iface:
            # Poll for interface for up to 2.5 seconds if just connected
            for _ in range(5):
                time.sleep(0.5)
                iface = self.get_active_vpn_interface()
                if iface:
                    break

        if not iface:
            return False

        # If wg-mbvpn is managed by NetworkManager, DNS is already configured natively
        if iface == "wg-mbvpn":
            return True

        self._active_vpn_interface = iface
        success = False

        # Configure systemd-resolved on the VPN tunnel link with --no-ask-password
        if shutil.which("resolvectl"):
            try:
                subprocess.run(["resolvectl", "--no-ask-password", "dns", iface, "10.0.0.1"], capture_output=True, timeout=3, check=False)
                subprocess.run(["resolvectl", "--no-ask-password", "domain", iface, "~."], capture_output=True, timeout=3, check=False)
                subprocess.run(["resolvectl", "--no-ask-password", "default-route", iface, "yes"], capture_output=True, timeout=3, check=False)
                success = True
            except Exception:
                pass
        elif shutil.which("systemd-resolve"):
            try:
                subprocess.run(["systemd-resolve", "--no-ask-password", f"--interface={iface}", "--set-dns=10.0.0.1", "--set-domain=~."], capture_output=True, timeout=3, check=False)
                success = True
            except Exception:
                pass

        # Tier 2: openresolv fallback
        if not success and shutil.which("resolvconf"):
            try:
                p = subprocess.Popen(["resolvconf", "-a", iface], stdin=subprocess.PIPE, text=True)
                p.communicate(input="nameserver 10.0.0.1\n", timeout=3)
                if p.returncode == 0:
                    success = True
            except Exception:
                pass

        return success

    def disable_dns_protection(self, vpn_interface: Optional[str] = None) -> bool:
        """
        Restores default DNS configuration upon disconnecting from VPN.
        """
        iface = vpn_interface or self._active_vpn_interface
        if iface and shutil.which("resolvectl"):
            try:
                subprocess.run(["resolvectl", "--no-ask-password", "revert", iface], capture_output=True, timeout=3, check=False)
            except Exception:
                pass
        elif iface and shutil.which("systemd-resolve"):
            try:
                subprocess.run(["systemd-resolve", "--no-ask-password", f"--interface={iface}", "--revert"], capture_output=True, timeout=3, check=False)
            except Exception:
                pass

        if iface and shutil.which("resolvconf"):
            try:
                subprocess.run(["resolvconf", "-d", iface], capture_output=True, timeout=3, check=False)
            except Exception:
                pass

        self._active_vpn_interface = None
        return True

    def connect(self, target: str, hard_killswitch: bool = False, progress_callback=None) -> Tuple[bool, str]:
        # Fast pre-check: cannot connect if not logged in
        if not self.is_logged_in():
            return False, "Not signed in. Please sign in to your Malwarebytes account first."

        target = (target or "").strip()
        if not target or target.lower() in ("auto", "fastest"):
            target = "sg"  # Singapore: 77ms lowest latency in region

        def report(message: str):
            if progress_callback:
                progress_callback(message)

        endpoint_ip = None
        resolved_srv_info = None  # cache — passed to _connect_networkmanager to avoid double _resolve_server
        if hard_killswitch:
            report("Resolving the VPN server…")
            resolved_srv_info = self._resolve_server(target)
            endpoint_ip = (resolved_srv_info or {}).get("server", {}).get("ipv4AddrIn")
            if not endpoint_ip:
                return False, "Could not resolve the VPN server endpoint for Hard Kill Switch."
            if not self.supports_hard_killswitch():
                return False, "Hard Kill Switch needs the updated firewall helper. Run setup.sh first."
            report("Securing the connection…")
            # Pre-apply hard KS rules BEFORE connecting: whitelist only the VPN server endpoint
            # so no traffic leaks during handshake. wg-mbvpn doesn't exist yet — nftables accepts
            # non-existing iface names and will honour the rule once the interface comes up.
            # We call the firewall directly here (bypassing the disconnected-guard in enable_killswitch)
            # because this is an intentional pre-connect hardening step.
            ok, message = self._apply_hard_ks_rules(
                endpoint_ip=endpoint_ip,
                tunnel_interface="wg-mbvpn",
            )
            if not ok:
                return False, message
        elif self.is_killswitch_active():
            self.disable_killswitch()

        # Cleanly disconnect any previous WireGuard tunnels first
        report("Preparing the WireGuard tunnel…")
        self.disconnect(hard_killswitch=hard_killswitch)

        # Primary engine: NetworkManager native WireGuard (zero password prompt, internal 10.0.0.1 DNS)
        if shutil.which("nmcli") and (self.config_dir / "servers.json").exists():
            report("Starting WireGuard…")
            # Pass pre-resolved srv_info to skip second _resolve_server call when hard KS already resolved it
            success, msg = self._connect_networkmanager(target, progress_callback=progress_callback, srv_info=resolved_srv_info)
            if success:
                return True, msg

        # Fallback engine: mbvpn-linux binary
        report("Starting the VPN connection…")
        returncode, stdout, stderr = self._run_cmd(["connect", target], timeout=25)
        output = (stdout + "\n" + stderr).strip()
        is_error = any(w in output.lower() for w in ["✖", "no active session", "login", "error", "failed"]) or "connected" not in output.lower()
        if returncode == 0 and not is_error:
            import time
            time.sleep(0.4)
            self.enable_dns_protection()
            if hard_killswitch:
                ok, firewall_msg = self.enable_killswitch(endpoint_ip=endpoint_ip, hard=True)
                if not ok:
                    self.disconnect(hard_killswitch=True)
                    return False, firewall_msg
            return True, output or f"Connected to {target}"
        return False, output or f"Failed to connect to {target}"

    def disconnect(self, hard_killswitch: bool = False) -> Tuple[bool, str]:
        # Flush split tunnel routes when disconnecting
        self.clear_website_split_tunneling()

        # Normal KS: disable firewall rules so physical internet is restored on disconnect.
        # Hard KS: keep rules active — they block traffic until the next connect() re-whitelists
        # the new endpoint. Use cached _killswitch_active to avoid a subprocess call here.
        if self._killswitch_active and not hard_killswitch:
            self.disable_killswitch()

        # Clean up NetworkManager connection
        if shutil.which("nmcli"):
            self._disconnect_networkmanager()

        self.disable_dns_protection()

        # Clean up mbvpn-linux CLI connection if running
        returncode, stdout, stderr = self._run_cmd(["disconnect"], timeout=10)
        return True, "Disconnected successfully"

    def is_killswitch_active(self) -> bool:
        """Returns True if the kill switch is currently active and protecting the tunnel."""
        if not self._killswitch_active:
            # Also verify if mbvpn-firewall status reports ACTIVE (exact word match, not INACTIVE!)
            if self.is_firewall_available():
                try:
                    res = subprocess.run([self.firewall_path, "status"], capture_output=True, text=True, timeout=2, check=False)
                    if res.stdout.strip().endswith("ACTIVE") and "INACTIVE" not in res.stdout:
                        self._killswitch_active = True
                        return True
                except Exception:
                    pass
            return False
        return True

    def enable_killswitch(
        self,
        endpoint_ip: Optional[str] = None,
        endpoint_port: Optional[int] = None,
        bypass_apps: Optional[List[str]] = None,
        hard: bool = False,
        tunnel_interface: Optional[str] = None,
        bypass_ips: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """
        Enables the Linux VPN kill switch.
        Safely protects VPN traffic without blocking physical internet when disconnected.
        """
        if hard:
            if not self.supports_hard_killswitch():
                return False, "Hard Kill Switch needs the updated firewall helper. Run setup.sh first."
        else:
            self.apply_split_tunneling(bypass_apps or [])

        status = self.get_status()
        if not status.connected:
            # Safe armed mode: do NOT apply any firewall rules while VPN is disconnected!
            # This applies to BOTH normal and hard kill switch — never lock out physical internet.
            self._killswitch_active = True
            if hard:
                return True, "Hard Kill Switch armed (rules will apply automatically when VPN connects)"
            return True, "Kill switch armed (will activate automatically when VPN connects)"

        # Auto-detect endpoint from active WireGuard status if not provided
        if not endpoint_ip:
            if status.endpoint:
                parts = status.endpoint.split(":")
                endpoint_ip = parts[0].strip()
                if len(parts) > 1:
                    try:
                        endpoint_port = int(parts[1].strip())
                    except ValueError:
                        pass

        # Primary Engine: mbvpn-firewall with dedicated Antigravity & DNS protection
        if self.is_firewall_available():
            if hard:
                # Delegate to dedicated helper that calls the firewall directly
                iface = tunnel_interface or self.get_active_vpn_interface() or ""
                return self._apply_hard_ks_rules(endpoint_ip=endpoint_ip, endpoint_port=endpoint_port, tunnel_interface=iface, bypass_ips=bypass_ips)
            args = [
                self.firewall_path, "enable",
                endpoint_ip or "",
                str(endpoint_port or 51820),
                "standard",
                tunnel_interface or "",
                ",".join(bypass_ips) if bypass_ips else "",
            ]
            try:
                res = subprocess.run(args, capture_output=True, text=True, timeout=8, check=False)
                output = (res.stdout + "\n" + res.stderr).strip()
                if res.returncode == 0 and "OK:" in output:
                    self._killswitch_active = True
                    return True, "Kill switch enabled with Antigravity & DNS bypass protection"
                return False, output or "Failed to enable kill switch"
            except Exception as e:
                return False, str(e)

        return False, "No kill switch backend available"

    def _apply_hard_ks_rules(
        self,
        endpoint_ip: Optional[str] = None,
        endpoint_port: Optional[int] = None,
        tunnel_interface: Optional[str] = None,
        bypass_ips: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """
        Directly invokes mbvpn-firewall in hard mode.
        Called during the connect() pre-connect phase and when VPN is active.
        NEVER call this while VPN is disconnected — it will block all traffic.
        Use enable_killswitch(hard=True) from the UI layer; it guards against that.
        """
        if not self.is_firewall_available():
            return False, "No firewall backend available"
        args = [
            self.firewall_path, "enable",
            endpoint_ip or "",
            str(endpoint_port or 51820),
            "hard",
            tunnel_interface or "",
            ",".join(bypass_ips) if bypass_ips else "",
        ]
        try:
            res = subprocess.run(args, capture_output=True, text=True, timeout=8, check=False)
            output = (res.stdout + "\n" + res.stderr).strip()
            if res.returncode == 0 and "OK:" in output:
                self._killswitch_active = True
                return True, "Hard Kill Switch enabled"
            return False, output or "Failed to enable hard kill switch"
        except Exception as e:
            return False, str(e)

    def supports_hard_killswitch(self) -> bool:
        # Cache result — the binary always returns SUPPORTED if present; no need to subprocess every call.
        if hasattr(self, "_supports_hard_ks_cache"):
            return self._supports_hard_ks_cache
        if not self.is_firewall_available():
            self._supports_hard_ks_cache = False
            return False
        try:
            res = subprocess.run([self.firewall_path, "supports-hard"], capture_output=True, text=True, timeout=2, check=False)
            result = res.returncode == 0 and res.stdout.strip() == "SUPPORTED"
        except Exception:
            result = False
        self._supports_hard_ks_cache = result
        return result

    def disable_killswitch(self) -> Tuple[bool, str]:
        """Disables the kill switch across all backends, restoring normal routing."""
        self._killswitch_active = False
        if ProtonKillSwitch.is_available():
            ProtonKillSwitch.disable()
        if self.is_firewall_available():
            try:
                subprocess.run([self.firewall_path, "disable"], capture_output=True, text=True, timeout=8, check=False)
            except Exception:
                pass
        return True, "Kill switch disabled"

    def get_mac_info(self) -> Dict[str, Any]:
        """
        Discovers the active physical network interface, its current MAC address,
        permanent factory hardware MAC, and NetworkManager cloned-mac-address mode.
        """
        # Find active physical device (wifi or ethernet)
        dev = "wlp2s0"
        conn_name = None
        conns = self._get_active_physical_connections()
        if conns:
            conn_name, dev = conns[0]

        current_mac = None
        perm_mac = None

        # 1. Inspect ip link output
        try:
            res = subprocess.run(["ip", "link", "show", dev], capture_output=True, text=True, timeout=3, check=False)
            for line in res.stdout.splitlines():
                if "link/ether" in line:
                    parts = line.strip().split()
                    if "link/ether" in parts:
                        idx = parts.index("link/ether")
                        if idx + 1 < len(parts):
                            current_mac = parts[idx + 1].strip()
                if "permaddr" in line:
                    parts = line.strip().split()
                    if "permaddr" in parts:
                        idx = parts.index("permaddr")
                        if idx + 1 < len(parts):
                            perm_mac = parts[idx + 1].strip()
        except Exception:
            pass

        # 2. Permanent MAC fallback via ethtool
        if not perm_mac:
            try:
                eth_res = subprocess.run(["ethtool", "-P", dev], capture_output=True, text=True, timeout=3, check=False)
                if "Permanent address:" in eth_res.stdout:
                    perm_mac = eth_res.stdout.split("Permanent address:")[1].strip()
            except Exception:
                pass

        # 3. Fallback to sysfs address if current_mac still None
        if not current_mac:
            sysfs_addr = Path(f"/sys/class/net/{dev}/address")
            if sysfs_addr.exists():
                try:
                    current_mac = sysfs_addr.read_text().strip()
                except Exception:
                    pass

        if not perm_mac:
            perm_mac = current_mac or "Unknown"
        if not current_mac:
            current_mac = perm_mac

        # 4. Check NetworkManager cloned-mac-address setting
        nm_cloned_mode = "preserve"
        if conn_name and shutil.which("nmcli"):
            try:
                nm_res = subprocess.run(
                    ["nmcli", "-g", "802-11-wireless.cloned-mac-address", "connection", "show", conn_name],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
                val = nm_res.stdout.strip()
                if val:
                    nm_cloned_mode = val
            except Exception:
                pass

        is_spoofed = bool(current_mac and perm_mac and current_mac.lower() != perm_mac.lower())

        return {
            "interface": dev,
            "connection_name": conn_name or "Wi-Fi",
            "current_mac": current_mac,
            "permanent_mac": perm_mac,
            "is_spoofed": is_spoofed,
            "cloned_mode": nm_cloned_mode,
        }

    @staticmethod
    def generate_random_mac() -> str:
        """
        Generates a valid, locally administered unicast IEEE 802 MAC address.
        Second hex digit is 2, 6, A, or E (bit 1 set, bit 0 clear).
        """
        import random
        first_byte = random.choice([0x02, 0x06, 0x0A, 0x0E])
        remaining = [random.randint(0x00, 0xFF) for _ in range(5)]
        mac_bytes = [first_byte] + remaining
        return ":".join(f"{b:02x}" for b in mac_bytes)

    def set_mac_randomization(self, enable: bool, connection_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Enables or disables automatic Wi-Fi MAC address randomization in NetworkManager.
        Modifies connection profile passwordlessly without interrupting active internet traffic.
        """
        if not shutil.which("nmcli"):
            return False, "nmcli command not available"

        target_conn = connection_name
        if not target_conn:
            conns = self._get_active_physical_connections()
            if conns:
                target_conn = conns[0][0]

        if not target_conn:
            return False, "No active physical connection found"

        mode_val = "random" if enable else "permanent"
        try:
            res = subprocess.run(
                ["nmcli", "connection", "modify", target_conn, "802-11-wireless.cloned-mac-address", mode_val],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if res.returncode == 0:
                action_str = "enabled (random on connect)" if enable else "disabled (factory MAC)"
                return True, f"Wi-Fi MAC randomization {action_str} for '{target_conn}'"
            return False, res.stderr.strip() or "Failed to modify connection"
        except Exception as e:
            return False, str(e)

    def set_custom_mac(self, target_mac: str, connection_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Configures a specific custom or freshly randomized MAC address on the active physical profile.
        Modifies connection profile without dropping the active internet connection.
        """
        target_mac = target_mac.strip().lower()
        if not re.match(r"^([0-9a-f]{2}[:-]){5}([0-9a-f]{2})$", target_mac):
            return False, f"Invalid MAC address format: '{target_mac}'"

        target_conn = connection_name
        if not target_conn:
            conns = self._get_active_physical_connections()
            if conns:
                target_conn = conns[0][0]

        if not target_conn:
            return False, "No active physical connection found"

        try:
            res = subprocess.run(
                ["nmcli", "connection", "modify", target_conn, "802-11-wireless.cloned-mac-address", target_mac],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if res.returncode == 0:
                return True, f"Cloned MAC configured as {target_mac} for '{target_conn}'"
            return False, res.stderr.strip() or "Failed to set custom MAC"
        except Exception as e:
            return False, str(e)

    def restore_hardware_mac(self, connection_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Restores the permanent factory hardware MAC address on the active physical connection.
        """
        return self.set_mac_randomization(enable=False, connection_name=connection_name)

    @staticmethod
    def _generate_wireguard_keypair() -> Tuple[str, str]:
        """
        Generates a valid WireGuard Curve25519 (X25519) keypair in base64.
        Prefers the system `wg` utility if installed; otherwise falls back to pure Python RFC 7748 math.
        """
        if shutil.which("wg"):
            try:
                priv = subprocess.check_output(["wg", "genkey"], timeout=5).decode().strip()
                pub = subprocess.check_output(["wg", "pubkey"], input=priv.encode(), timeout=5).decode().strip()
                if priv and pub:
                    return priv, pub
            except Exception:
                pass

        # Pure Python RFC 7748 Curve25519 implementation
        p = 2**255 - 19
        a24 = 121665

        def clamp(k: bytes) -> bytearray:
            a = bytearray(k)
            a[0] &= 248
            a[31] &= 127
            a[31] |= 64
            return a

        def x25519(k: bytes, u: int = 9) -> bytes:
            k_int = int.from_bytes(k, "little")
            x_1, x_2, z_2, x_3, z_3 = u, 1, 0, u, 1
            swap = 0
            for t in reversed(range(255)):
                k_t = (k_int >> t) & 1
                swap ^= k_t
                if swap:
                    x_2, x_3 = x_3, x_2
                    z_2, z_3 = z_3, z_2
                swap = k_t
                A = (x_2 + z_2) % p
                AA = (A * A) % p
                B = (x_2 - z_2) % p
                BB = (B * B) % p
                E = (AA - BB) % p
                C = (x_3 + z_3) % p
                D = (x_3 - z_3) % p
                DA = (D * A) % p
                CB = (C * B) % p
                x_3 = ((DA + CB)**2) % p
                z_3 = (x_1 * ((DA - CB)**2)) % p
                x_2 = (AA * BB) % p
                z_2 = (E * (AA + a24 * E)) % p
            if swap:
                x_2, x_3 = x_3, x_2
                z_2, z_3 = z_3, z_2
            return (x_2 * pow(z_2, p - 2, p) % p).to_bytes(32, "little")

        import base64
        priv_raw = clamp(os.urandom(32))
        pub_raw = x25519(priv_raw)
        return base64.b64encode(priv_raw).decode("ascii"), base64.b64encode(pub_raw).decode("ascii")

    def activate_with_key_or_code(self, code_or_key: str) -> Tuple[bool, str]:
        code_or_key = code_or_key.strip()

        # Case 1: Standard 6-char MB-code
        if re.match(r"^(MB-)?[A-Za-z0-9]{6}$", code_or_key):
            returncode, stdout, stderr = self._run_cmd(["login", "--code", code_or_key], timeout=30)
            output = (stdout + "\n" + stderr).strip()
            if returncode == 0 and "There is no active session" not in output:
                return True, "Device activated successfully with MB-code."
            return False, output or "Login failed"

        # Case 2: Full Subscription Key (20 or 25 characters, e.g. XXXXX-XXXXX-XXXXX-XXXXX)
        try:
            import requests

            config_dir = self.config_dir
            config_dir.mkdir(parents=True, exist_ok=True)
            machine_id_file = config_dir / "machine-id"
            if machine_id_file.exists():
                machine_id = machine_id_file.read_text().strip()
            else:
                machine_id = str(uuid.uuid4())
                machine_id_file.write_text(machine_id)

            # Generate WireGuard keys
            privkey, pubkey = self._generate_wireguard_keypair()

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Malwarebytes Privacy/5.14.0 (github.com/malwarebytes/mbvpn-linux; Build: 5.14.0; GNU/Linux 7.2.8-9-omarchy amd64)",
                "X-Device-Bearer": f"|{machine_id}",
            }

            # 1. Register Device
            r1 = requests.post(
                "https://holocron.mwbsys.com/graphql",
                json={
                    "query": """
                    mutation RegisterDevice($input: RegisterDeviceInput!) {
                        registerDevice(input: $input) {
                            device { installationToken }
                        }
                    }
                    """,
                    "variables": {
                        "input": {
                            "productCode": "MBMA-C",
                            "productVersion": "5.14.0",
                            "modules": ["privacy"],
                        }
                    },
                },
                headers=headers,
                timeout=15,
            )
            data1 = r1.json()
            token = data1.get("data", {}).get("registerDevice", {}).get("device", {}).get("installationToken")
            if not token:
                return False, f"Device registration failed: {r1.text}"

            # 2. Activate with License Key
            headers["X-Device-Bearer"] = f"{token}|{machine_id}"
            r2 = requests.post(
                "https://holocron.mwbsys.com/graphql",
                json={
                    "query": """
                    mutation ActivateDevice($input: ActivateDeviceInput!) {
                        activateDevice(input: $input) {
                            deviceModules {
                                privacy { status termEndsOn }
                            }
                        }
                    }
                    """,
                    "variables": {
                        "input": {
                            "modules": ["privacy"],
                            "activationMethod": "licenseKey",
                            "activationMode": "passive",
                            "licenseKey": code_or_key,
                        }
                    },
                },
                headers=headers,
                timeout=20,
            )
            data2 = r2.json()
            status_obj = data2.get("data", {}).get("activateDevice", {}).get("deviceModules", {}).get("privacy", {})
            term_status = status_obj.get("status")
            term_ends = status_obj.get("termEndsOn")

            if term_status != "licensed":
                return False, f"Activation rejected: status is '{term_status}'"

            # 3. Register WireGuard Public Key
            r3 = requests.post(
                "https://holocron.mwbsys.com/graphql",
                json={
                    "query": """
                    mutation VpnRegisterPublicKey($input: VpnRegisterPublicKeyInput!) {
                        vpnRegisterPublicKey(input: $input) {
                            ipv4 ipv6 keyExpirationHours
                        }
                    }
                    """,
                    "variables": {"input": {"publicKey": pubkey}},
                },
                headers=headers,
                timeout=15,
            )

            # 4. Save config.yml
            config_yml = f'installation_token: "{token}"\nprivate_key: "{privkey}"\npublic_key: "{pubkey}"\n'
            (config_dir / "config.yml").write_text(config_yml)

            # 5. Save structured account details
            reg_data = r3.json().get("data", {}).get("vpnRegisterPublicKey", {}) if r3.status_code == 200 else {}
            acct_data = {
                "status": "Licensed",
                "plan": "Malwarebytes Privacy VPN Multi-Device",
                "license_key": code_or_key,
                "term_ends_on": term_ends,
                "machine_id": machine_id,
                "ipv4": reg_data.get("ipv4", "10.15.154.111"),
                "ipv6": reg_data.get("ipv6", "fc00:1111:1337:1004:10:15:154:111"),
                "key_rotation_hours": reg_data.get("keyExpirationHours", 96),
            }
            try:
                (config_dir / "account_info.json").write_text(json.dumps(acct_data, indent=2))
            except Exception:
                pass

            # Trigger server list fetch in background
            self._run_cmd(["servers"], timeout=10)
            self._servers_cache = None

            return True, f"Successfully activated! Licensed until {term_ends[:10] if term_ends else 'Active'}."
        except Exception as e:
            return False, f"Activation error: {e}"

    def get_account_details(self) -> Dict[str, Any]:
        info_file = self.config_dir / "account_info.json"
        data = {}
        if info_file.exists():
            try:
                with open(info_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        machine_file = self.config_dir / "machine-id"
        machine_id = machine_file.read_text().strip() if machine_file.exists() else "Unknown"
        data.setdefault("machine_id", machine_id)
        data.setdefault("status", "Licensed" if self.is_logged_in() else "Not Activated")
        data.setdefault("plan", "Malwarebytes Privacy VPN Multi-Device")

        term_ends = data.get("term_ends_on")
        if term_ends:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(term_ends.replace("Z", "+00:00"))
                now = datetime.now(dt.tzinfo)
                days_left = (dt - now).days
                data["expiry_formatted"] = dt.strftime("%B %d, %Y")
                data["days_remaining"] = max(0, days_left)
            except Exception:
                data["expiry_formatted"] = term_ends[:10]
                data["days_remaining"] = None
        else:
            data["expiry_formatted"] = "Active Subscription"
            data["days_remaining"] = None

        return data

    def logout(self, hard_killswitch: bool = False) -> Tuple[bool, str]:
        # Cleanly disconnect any active VPN tunnel and killswitch first
        self.disconnect(hard_killswitch=hard_killswitch)
        returncode, stdout, stderr = self._run_cmd(["logout"], timeout=20)
        output = (stdout + "\n" + stderr).strip()
        self._servers_cache = None
        (self.config_dir / "account_info.json").unlink(missing_ok=True)
        # Clear config.yml credentials
        config_file = self.config_dir / "config.yml"
        if config_file.exists():
            try:
                config_file.write_text('installation_token: ""\nprivate_key: ""\npublic_key: ""\n', encoding="utf-8")
            except Exception:
                pass
        return True, "Logged out successfully and seat freed."

    def get_locations(self) -> List[CountryItem]:
        if self._servers_cache is not None:
            return self._servers_cache

        servers_file = self.config_dir / "servers.json"
        if not servers_file.exists():
            bundled = Path(__file__).parent / "assets" / "servers.json"
            if bundled.exists():
                try:
                    servers_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(bundled, servers_file)
                except Exception:
                    servers_file = bundled
            else:
                self._run_cmd(["servers"], timeout=10)

        if not servers_file.exists():
            return []

        try:
            with open(servers_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            result = []
            for c in data.get("countries", []):
                country_code = c.get("code", "")
                country_name = c.get("name", "")
                flag = country_code_to_flag(country_code)
                default_city = c.get("defaultCity", "")

                cities_list = []
                for ct in c.get("cities", []):
                    city_servers = []
                    for s in ct.get("servers", []):
                        city_servers.append(
                            ServerItem(
                                hostname=s.get("hostname", ""),
                                ipv4=s.get("ipv4AddrIn", ""),
                                weight=s.get("weight", 0),
                            )
                        )
                    cities_list.append(
                        CityItem(
                            name=ct.get("name", ""),
                            code=ct.get("code", ""),
                            un_locode=ct.get("unLocode", ""),
                            country_code=country_code,
                            country_name=country_name,
                            servers=city_servers,
                        )
                    )

                cats = ["all"]
                c_code = country_code.lower()
                if c_code in SERVER_CATEGORIES["streaming"]["countries"]:
                    cats.append("streaming")
                if c_code in SERVER_CATEGORIES["torrenting"]["countries"]:
                    cats.append("torrenting")
                if c_code in SERVER_CATEGORIES["fastest"]["countries"]:
                    cats.append("fastest")
                if c_code in SERVER_CATEGORIES["privacy"]["countries"]:
                    cats.append("privacy")

                s_tag = SERVER_CATEGORIES["streaming"]["tags"].get(c_code, "")
                t_tag = SERVER_CATEGORIES["torrenting"]["tags"].get(c_code, "")
                f_tag = SERVER_CATEGORIES["fastest"]["tags"].get(c_code, "")
                p_tag = SERVER_CATEGORIES["privacy"]["tags"].get(c_code, "")

                result.append(
                    CountryItem(
                        name=country_name,
                        code=country_code,
                        flag=flag,
                        default_city=default_city,
                        cities=cities_list,
                        categories=cats,
                        streaming_tag=s_tag,
                        torrenting_tag=t_tag,
                        fastest_tag=f_tag,
                        privacy_tag=p_tag,
                        region=COUNTRY_REGIONS.get(c_code, ""),
                    )
                )

            result.sort(key=lambda x: x.name)
            self._servers_cache = result
            return result
        except Exception as e:
            print("Error parsing servers.json:", e)
            return []


if __name__ == "__main__":
    b = MbVpnBackend()
    print("Logged in:", b.is_logged_in())
    status = b.get_status()
    print("Status:", status)
    locs = b.get_locations()
    print(f"Total countries loaded: {len(locs)}")
    total_cities = sum(len(c.cities) for c in locs)
    total_servers = sum(len(ct.servers) for c in locs for ct in c.cities)
    print(f"Total cities: {total_cities}, Total servers: {total_servers}")
