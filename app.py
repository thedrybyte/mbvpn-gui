#!/usr/bin/env python3
"""
Malwarebytes Privacy VPN - Tier-1 Native Linux Desktop Client
Custom-crafted for Arch Linux, Hyprland, and Wayland environments.
Features official Malwarebytes cyber aesthetic, 149 global WireGuard servers,
real-time telemetry, and direct license activation.
"""

import json
import math
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango

from backend import (
    CityItem,
    ConnectionStatus,
    CountryItem,
    MbVpnBackend,
    country_code_to_flag,
)
from tray import init_tray

APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"

# Exact Malwarebytes Privacy VPN UI Design Language & Themes
CUSTOM_CSS = """
/* Malwarebytes Privacy - Modern Commercial VPN System */
window, window.background, window.mbvpn-window, .mbvpn-window, .mullvad-window {
    background-color: #0d111a;
    color: #e2e8f0;
    min-width: 360px;
    min-height: 500px;
    font-family: "Liberation Sans", "Inter", "Cantarell", system-ui, -apple-system, sans-serif;
}

.mbvpn-window headerbar, .mullvad-window headerbar {
    background-color: #0f1422;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    color: #ffffff;
    min-height: 44px;
    padding-left: 10px;
    padding-right: 10px;
}

.mbvpn-header-badge {
    background: rgba(14, 165, 233, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.32);
    border-radius: 3px;
    font-size: 8.5px;
    font-weight: 800;
    letter-spacing: 0.9px;
    padding: 1px 5px;
    margin-left: 6px;
}

.mbvpn-header-group {
    margin-left: 2px;
}

.mbvpn-header-group button.flat {
    padding: 0;
    min-width: 28px;
    min-height: 28px;
    background: transparent;
    border: none;
    box-shadow: none;
}

.mbvpn-header-title, .mullvad-header-title {
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 0.5px;
    color: #ffffff;
}

.mbvpn-window scrolledwindow, .mullvad-window scrolledwindow {
    background-color: #0d111a;
}

/* Modern Hero Status Card with Ambient Sapphire Glow */
.mbvpn-hero-card, .mullvad-banner {
    border-radius: 16px;
    padding: 16px 18px 14px 18px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 4px 16px rgba(0, 0, 0, 0.3);
    background-clip: padding-box;
}

.mbvpn-hero-unsecured, .mullvad-banner-unsecured {
    background-color: #0f1422;
    background-image: url('file://__ASSETS_DIR__/bg_vpn_disconnected_atlas.png');
    background-size: cover;
    background-position: center;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 4px 16px rgba(0, 0, 0, 0.35);
    color: #ffffff;
}

.mbvpn-hero-secured, .mullvad-banner-secured {
    background-color: #0a1324;
    background-image: url('file://__ASSETS_DIR__/bg_vpn_connected_atlas.png');
    background-size: cover;
    background-position: center;
    border: 1px solid rgba(59, 130, 246, 0.45);
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 0 20px rgba(37, 99, 235, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    color: #ffffff;
}

.mbvpn-hero-connecting, .mullvad-banner-connecting {
    background-color: #0f1c30;
    background-image: url('file://__ASSETS_DIR__/bg_vpn_connected_atlas.png');
    background-size: cover;
    background-position: center;
    border: 1px solid rgba(56, 189, 248, 0.5);
    color: #ffffff;
}

.mbvpn-status-sub, .mullvad-status-sub {
    font-size: 12px;
    font-weight: 500;
    color: #94a3b8;
    margin-top: 3px;
}


.official-flag-icon {
    border-radius: 9999px;
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.12), 0 2px 6px rgba(0, 0, 0, 0.35);
    border: none;
}

.mbvpn-country, .mullvad-country {
    font-size: 13.5px;
    font-weight: 600;
    color: #f8fafc;
    letter-spacing: 0.1px;
}

.mbvpn-city, .mullvad-city {
    font-size: 11.5px;
    font-weight: 400;
    color: #94a3b8;
    margin-top: 1.5px;
}

.mbvpn-loc-chevron {
    color: #64748b;
    font-weight: 500;
    font-size: 13px;
    transition: all 160ms ease;
}

/* Modern Security & Privacy Panel */
.mbvpn-details-card, .mullvad-details-card {
    background: #141c2e;
    border-radius: 14px;
    padding: 12px 14px 10px 14px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 4px 12px rgba(0, 0, 0, 0.25);
    background-clip: padding-box;
}

.mbvpn-details-header, .mullvad-details-header {
    font-size: 10.5px;
    font-weight: 800;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #94a3b8;
}

.mbvpn-proto-badge {
    font-size: 9.5px;
    font-weight: 700;
    color: #38bdf8;
    background: rgba(14, 165, 233, 0.12);
    border: 1px solid rgba(14, 165, 233, 0.25);
    border-radius: 9999px;
    padding: 1px 8px;
}

/* Recessed Single Container Network Panel with Symmetric Padding */
.mbvpn-network-panel {
    background: rgba(10, 15, 26, 0.75);
    border-radius: 12px;
    padding: 12px 16px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.35);
}

separator.mbvpn-v-sep {
    background-color: rgba(255, 255, 255, 0.08);
    min-width: 1px;
    margin: 0 16px;
}

separator.mbvpn-h-sep {
    background-color: rgba(255, 255, 255, 0.06);
    min-height: 1px;
    margin: 10px 0;
}

.mbvpn-panel-label {
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #94a3b8;
}

.mbvpn-time-title {
    color: #aeb8c7;
    font-size: 11px;
    font-weight: 500;
}

.mbvpn-time-total {
    color: #f1f4f8;
    font-size: 17px;
    font-weight: 600;
}

.mbvpn-time-caption {
    color: #8994a4;
    font-size: 9px;
}

.mbvpn-panel-val {
    font-size: 13px;
    font-weight: 700;
    color: #10b981;
}

.mbvpn-panel-sub {
    font-size: 11px;
    font-weight: 600;
    color: #cbd5e1;
}

.mbvpn-panel-sub.active {
    color: #10b981;
}

.mbvpn-panel-sub.armed {
    color: #f59e0b;
}

.mbvpn-panel-sub.disabled {
    color: #94a3b8;
}

/* Sleek iOS/macOS Toggle Switch with 44px Touch Target */
.mbvpn-switch-target {
    min-width: 44px;
    min-height: 44px;
}

switch.mbvpn-ios-switch {
    background-color: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 9999px;
    min-width: 44px;
    min-height: 24px;
    outline: none;
    transition: all 180ms cubic-bezier(0.4, 0, 0.2, 1);
}

switch.mbvpn-ios-switch:checked {
    background: #0ca987;
    border-color: rgba(16, 185, 129, 0.4);
    box-shadow: 0 0 8px rgba(16, 185, 129, 0.3);
}

switch.mbvpn-ios-switch slider {
    background-color: #cbd5e1;
    border-radius: 9999px;
    min-width: 18px;
    min-height: 18px;
    outline: none;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
    transition: all 180ms cubic-bezier(0.4, 0, 0.2, 1);
}

switch.mbvpn-ios-switch:checked slider {
    background-color: #ffffff;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.5);
}

/* Monospace & Tabular Numbers */
.mbvpn-mono-num {
    font-family: "JetBrains Mono", "Fira Code", "Liberation Mono", "DejaVu Sans Mono", monospace;
    font-feature-settings: "tnum" 1;
}

.mbvpn-tile {
    background: rgba(10, 15, 26, 0.65);
    border-radius: 10px;
    padding: 8px 12px;
    border: 1px solid rgba(255, 255, 255, 0.06);
}

.mbvpn-tile-label {
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #94a3b8;
}

.mbvpn-tile-val {
    font-size: 13.5px;
    font-weight: 700;
    color: #10b981;
    margin-top: 2px;
}

.mbvpn-traffic-strip {
    padding-top: 2px;
}

.mbvpn-details-subtle, .mullvad-details-subtle {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    color: #94a3b8;
}

.mbvpn-traffic-down-arrow {
    color: #10b981;
    font-weight: 800;
    font-size: 12px;
    margin-right: 2px;
}

.mbvpn-traffic-up-arrow {
    color: #38bdf8;
    font-weight: 800;
    font-size: 12px;
    margin-left: 8px;
    margin-right: 2px;
}

.mbvpn-details-val, .mullvad-details-val {
    font-size: 13px;
    font-weight: 700;
    color: #f1f5f9;
}

.mbvpn-details-val.active {
    color: #10b981;
}

.mbvpn-details-val.disabled {
    color: #94a3b8;
}

.mbvpn-details-badge, .mullvad-details-badge {
    font-size: 10px;
    font-weight: 700;
    color: #10b981;
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 9999px;
    padding: 2px 10px;
}

.mbvpn-details-badge-armed, .mullvad-details-badge-armed {
    font-size: 10px;
    font-weight: 700;
    color: #fbbf24;
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-radius: 9999px;
    padding: 2px 10px;
}

.mbvpn-details-badge-off, .mullvad-details-badge-off {
    font-size: 10px;
    font-weight: 700;
    color: #94a3b8;
    background: rgba(100, 116, 139, 0.15);
    border: 1px solid rgba(100, 116, 139, 0.25);
    border-radius: 9999px;
    padding: 2px 10px;
}

/* Footer / Creator Credit */
.mbvpn-credit-box, .mullvad-credit-box {
    margin-top: 4px;
    padding-top: 2px;
    padding-bottom: 2px;
}

.mbvpn-credit-label, .mullvad-credit-label {
    font-size: 11px;
    color: #64748b;
    letter-spacing: 0.3px;
    font-family: "Liberation Sans", "Inter", sans-serif;
}

.mbvpn-credit-label a, .mullvad-credit-label a {
    color: #38bdf8;
    text-decoration: none;
    font-weight: 600;
}

.mbvpn-credit-label a:hover, .mullvad-credit-label a:hover {
    color: #7dd3fc;
    text-decoration: underline;
}

/* Modern Preferences & Lists */
.mbvpn-window list, .mullvad-window list {
    background-color: #141c2e;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

.mbvpn-window row, .mullvad-window row {
    background-color: #141c2e;
    color: #ffffff;
}

.mbvpn-window row:hover, .mullvad-window row:hover {
    background-color: #1c263c;
}

.mbvpn-window preferencesgroup > label, .mullvad-window preferencesgroup > label {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #8ca0b3;
    margin-bottom: 6px;
}

.badge-flag {
    font-size: 20px;
}

/* Category Filter Pills */
.cat-box-container {
    background-color: rgba(17, 23, 38, 0.8);
    border-radius: 8px;
    padding: 3px;
    border: 1px solid rgba(255, 255, 255, 0.06);
}

.cat-pill {
    border-radius: 6px;
    padding: 5px 0px;
    font-size: 11px;
    font-weight: 600;
    background-color: transparent;
    color: #94a3b8;
    border: none;
    transition: all 140ms ease;
}

.cat-pill:hover {
    background-color: rgba(255, 255, 255, 0.08);
    color: #ffffff;
}

.cat-pill-active {
    background: #0066ff;
    color: #ffffff;
    box-shadow: 0 1px 4px rgba(0, 102, 255, 0.4);
}

.category-tag {
    font-size: 11px;
    font-weight: 500;
    color: #38bdf8;
    margin-top: 2px;
}

/* Unified dashboard palette */
window.mbvpn-window, window.mullvad-window {
    background-color: #090e15;
    background-image: none;
    color: #f4f7fc;
    min-width: 360px;
    min-height: 540px;
}

.mbvpn-window scrolledwindow, .mullvad-window scrolledwindow {
    background-color: #090e15;
    background-image: none;
}

.mbvpn-window headerbar, .mullvad-window headerbar {
    background-color: #090e15;
    background-image: none;
    border-bottom: 1px solid #182333;
    min-height: 48px;
}

/* Top navigation icon buttons: pure, borderless, shadowless minimal icons */
.mbvpn-header-group button,
.mbvpn-header-group button.flat,
.mbvpn-window headerbar button,
.mullvad-window headerbar button {
    background: none;
    background-color: transparent;
    background-image: none;
    border: none;
    box-shadow: none;
    outline: none;
    border-radius: 0;
    min-width: 28px;
    min-height: 28px;
    padding: 0;
    transition: all 120ms ease;
    color: #94a3b8;
}

.mbvpn-header-group button image,
.mbvpn-header-group button.flat image,
.mbvpn-window headerbar button image,
.mullvad-window headerbar button image {
    -gtk-icon-size: 15px;
    opacity: 0.82;
    color: #94a3b8;
    transition: all 120ms ease;
}

.mbvpn-header-group button:hover,
.mbvpn-header-group button.flat:hover,
.mbvpn-header-group button:focus,
.mbvpn-header-group button.flat:focus,
.mbvpn-window headerbar button:hover,
.mullvad-window headerbar button:hover {
    background: none;
    background-color: transparent;
    background-image: none;
    border: none;
    box-shadow: none;
    outline: none;
    color: #ffffff;
}

.mbvpn-header-group button:hover image,
.mbvpn-header-group button.flat:hover image,
.mbvpn-header-group button:focus image,
.mbvpn-header-group button.flat:focus image,
.mbvpn-window headerbar button:hover image,
.mullvad-window headerbar button:hover image {
    opacity: 1;
    color: #ffffff;
}

.mbvpn-header-group button:active,
.mbvpn-header-group button.flat:active,
.mbvpn-window headerbar button:active,
.mullvad-window headerbar button:active {
    background: none;
    background-color: transparent;
    background-image: none;
    border: none;
    box-shadow: none;
    outline: none;
    color: #38bdf8;
    transform: scale(0.92);
}

.mbvpn-header-group button:active image,
.mbvpn-header-group button.flat:active image,
.mbvpn-window headerbar button:active image,
.mullvad-window headerbar button:active image {
    color: #38bdf8;
    opacity: 1;
}

/* Close button: pure icon hover without any background or shadow */
.mbvpn-header-group button.mbvpn-btn-close,
.mbvpn-header-group button.flat.mbvpn-btn-close {
    background: none;
    background-color: transparent;
    background-image: none;
    border: none;
    box-shadow: none;
    outline: none;
    color: #94a3b8;
}

.mbvpn-header-group button.mbvpn-btn-close image,
.mbvpn-header-group button.flat.mbvpn-btn-close image {
    -gtk-icon-size: 12px;
    opacity: 0.82;
    color: #94a3b8;
    transition: all 120ms ease;
}

.mbvpn-header-group button.mbvpn-btn-close:hover,
.mbvpn-header-group button.flat.mbvpn-btn-close:hover,
.mbvpn-header-group button.mbvpn-btn-close:focus,
.mbvpn-header-group button.flat.mbvpn-btn-close:focus {
    background: none;
    background-color: transparent;
    background-image: none;
    border: none;
    box-shadow: none;
    outline: none;
    color: #f87171;
}

.mbvpn-header-group button.mbvpn-btn-close:hover image,
.mbvpn-header-group button.flat.mbvpn-btn-close:hover image,
.mbvpn-header-group button.mbvpn-btn-close:focus image,
.mbvpn-header-group button.flat.mbvpn-btn-close:focus image {
    color: #f87171;
    opacity: 1;
}

.mbvpn-header-group button.mbvpn-btn-close:active,
.mbvpn-header-group button.flat.mbvpn-btn-close:active {
    background: none;
    background-color: transparent;
    background-image: none;
    border: none;
    box-shadow: none;
    outline: none;
    color: #ef4444;
    transform: scale(0.92);
}

.mbvpn-header-group button.mbvpn-btn-close:active image,
.mbvpn-header-group button.flat.mbvpn-btn-close:active image {
    color: #ef4444;
    opacity: 1;
}

/* Native window controls: pure transparent, shadowless */
.mbvpn-window windowcontrols button,
.mullvad-window windowcontrols button,
.mbvpn-window headerbar windowcontrols button,
.mullvad-window headerbar windowcontrols button {
    background: none;
    background-color: transparent;
    background-image: none;
    border: none;
    box-shadow: none;
    outline: none;
    min-width: 28px;
    min-height: 28px;
    padding: 0;
    transition: all 120ms ease;
    color: #94a3b8;
}

.mbvpn-window windowcontrols button:hover,
.mullvad-window windowcontrols button:hover,
.mbvpn-window headerbar windowcontrols button:hover,
.mullvad-window headerbar windowcontrols button:hover {
    background: none;
    background-color: transparent;
    background-image: none;
    border: none;
    box-shadow: none;
    outline: none;
    color: #f87171;
}

.mbvpn-window windowcontrols button image,
.mullvad-window windowcontrols button image {
    opacity: 0.82;
    color: #94a3b8;
    transition: all 120ms ease;
}

.mbvpn-window windowcontrols button:hover image,
.mullvad-window windowcontrols button:hover image,
.mbvpn-window headerbar windowcontrols button:hover image,
.mullvad-window headerbar windowcontrols button:hover image {
    opacity: 1;
    color: #f87171;
}

.mbvpn-header-badge {
    background: rgba(37, 99, 235, 0.14);
    color: #93b4ff;
    border-color: rgba(110, 150, 255, 0.22);
    border-radius: 5px;
    font-size: 9px;
    letter-spacing: 0.6px;
    padding: 2px 6px;
}

.mbvpn-hero-card, .mullvad-banner {
    border-radius: 16px;
    padding: 15px 18px 14px;
    border: 1px solid #253750;
    box-shadow: none;
    background-clip: padding-box;
}

.mbvpn-hero-unsecured, .mullvad-banner-unsecured {
    background-color: #142239;
    background-image: linear-gradient(115deg, #192b42 0%, #142239 100%);
    border-color: #253750;
}

.mbvpn-hero-secured, .mullvad-banner-secured {
    background-color: #122745;
    background-image: linear-gradient(115deg, #193451 0%, #122745 100%);
    border-color: #29415e;
    box-shadow: none;
}

.mbvpn-status-sub, .mullvad-status-sub {
    color: #c4d0e0;
    font-size: 12px;
}

.mbvpn-details-card, .mullvad-details-card {
    background: #111b29;
    border: 1px solid #1c2b3d;
    border-radius: 12px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.018);
    background-clip: padding-box;
}

.mbvpn-country, .mullvad-country {
    font-size: 14px;
    font-weight: 650;
    letter-spacing: 0;
}

.mbvpn-city, .mullvad-city {
    color: #a2adbd;
    font-size: 11.5px;
}

.mbvpn-details-card, .mullvad-details-card {
    padding: 14px 15px 13px;
    border-radius: 12px;
    background: #111b29;
    border-color: #1c2b3d;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.018);
}

.mbvpn-details-header, .mullvad-details-header {
    color: #f0f5fc;
    font-size: 11px;
    letter-spacing: 0;
    text-transform: none;
}

.mbvpn-panel-label, .mbvpn-details-subtle {
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.1px;
    text-transform: none;
    color: #a9b7ca;
}

.mbvpn-proto-badge {
    font-size: 10px;
    font-weight: 600;
    color: #9eb8e4;
}

.mbvpn-network-panel {
    background: transparent;
    border: none;
    border-top: 1px solid #263447;
    border-radius: 0;
    padding: 8px 0 0;
    box-shadow: none;
}

separator.mbvpn-v-sep {
    margin: 0 10px;
}

switch.mbvpn-ios-switch:checked {
    background: linear-gradient(135deg, #0ca987 0%, #078b70 100%);
    border-color: rgba(66, 211, 166, 0.4);
    box-shadow: 0 0 9px rgba(16, 185, 129, 0.18);
}

.mbvpn-proto-badge {
    color: #a9c3ff;
    background: transparent;
    border-color: transparent;
    border-radius: 4px;
    padding: 1px 0;
}

.mbvpn-panel-val, .mbvpn-panel-sub.active,
.mbvpn-details-badge, .mullvad-details-badge {
    color: #55c99a;
}

.mbvpn-details-subtle, .mullvad-details-subtle,
.mbvpn-panel-label, .mbvpn-tile-label {
    color: #a9bad1;
}

.mbvpn-window list, .mullvad-window list,
.mbvpn-window row, .mullvad-window row {
    background-color: #111620;
}

.mbvpn-window row:hover, .mullvad-window row:hover {
    background-color: #171e2b;
}

.mbvpn-hero-card, .mullvad-banner {
    padding: 15px 18px 14px;
    border-radius: 16px;
}

.mbvpn-hero-unsecured, .mullvad-banner-unsecured {
    background-color: #142239;
    background-image: linear-gradient(115deg, #192b42 0%, #142239 100%);
    border-color: #253750;
}

.mbvpn-hero-secured, .mullvad-banner-secured {
    background-color: #122745;
    background-image: linear-gradient(115deg, #193451 0%, #122745 100%);
    border-color: #29415e;
    box-shadow: none;
}

.mbvpn-details-card, .mullvad-details-card {
    background-color: #111b29;
    border-color: #223148;
    border-radius: 11px;
    box-shadow: none;
}

separator.mbvpn-v-sep {
    margin: 0 8px;
    opacity: 0.6;
}

separator.mbvpn-h-sep {
    margin: 8px 0;
    opacity: 0.65;
}

.mbvpn-network-panel {
    border-top-color: #223148;
    padding-top: 7px;
}

window, window.background, window.mbvpn-window, .mbvpn-window, .mullvad-window,
.mbvpn-window scrolledwindow, .mullvad-window scrolledwindow {
    background-color: #0b111a;
}

.mbvpn-window headerbar, .mullvad-window headerbar {
    background-color: #0d141f;
    border-bottom-color: #1a2636;
}

.mbvpn-hero-card, .mullvad-banner,
.mbvpn-details-card, .mullvad-details-card {
    border-radius: 12px;
    box-shadow: none;
}

.mbvpn-hero-card, .mullvad-banner {
    padding: 15px 18px 14px;
}

.mbvpn-hero-secured, .mullvad-banner-secured {
    background-color: #142b49;
    background-image: linear-gradient(112deg, #1a385a 0%, #142b49 100%);
    border-color: #294867;
}

.mbvpn-hero-unsecured, .mullvad-banner-unsecured {
    background-color: #142133;
    background-image: none;
    border-color: #263a51;
}

.mbvpn-details-card, .mullvad-details-card {
    background-color: #101b2a;
    border-color: #20334a;
}

.mbvpn-details-card, .mullvad-details-card {
    padding: 13px 15px 12px;
}

.mbvpn-network-panel {
    border-top-color: #263a52;
}

separator.mbvpn-v-sep, separator.mbvpn-h-sep {
    background-color: #263a52;
}

switch.mbvpn-ios-switch:checked {
    background: #0ba98b;
    border-color: #20b89d;
    box-shadow: none;
}

.mbvpn-status-sub, .mullvad-status-sub {
    color: #cad6e4;
    font-size: 12px;
}

.mbvpn-details-card, .mullvad-details-card {
    background: transparent;
    border: none;
    padding: 2px 0 0;
}

.mbvpn-details-header, .mullvad-details-header {
    color: #dce6f3;
    font-size: 12px;
    font-weight: 650;
}

.mbvpn-proto-badge {
    color: #9eb8dc;
    font-size: 10.5px;
}

.mbvpn-network-panel {
    background-color: #101b2a;
    border: 1px solid #20334a;
    border-radius: 12px;
    padding: 12px 15px;
}

.mbvpn-time-title {
    color: #b6c4d5;
    font-size: 11px;
}

.mbvpn-time-total {
    font-size: 18px;
    font-weight: 650;
}

.mbvpn-panel-label, .mbvpn-details-subtle {
    color: #b6c4d5;
    font-size: 10.5px;
}

/* App-owned accent so Adwaita controls never inherit the host desktop accent */
.mbvpn-window switch:not(.mbvpn-ios-switch),
.mullvad-window switch:not(.mbvpn-ios-switch) {
    background-color: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 9999px;
    outline: none;
}

.mbvpn-window switch:not(.mbvpn-ios-switch):checked,
.mullvad-window switch:not(.mbvpn-ios-switch):checked {
    background: #0ca987;
    border-color: rgba(16, 185, 129, 0.45);
    box-shadow: none;
}

.mbvpn-window switch:not(.mbvpn-ios-switch) slider,
.mullvad-window switch:not(.mbvpn-ios-switch) slider {
    background-color: #cbd5e1;
    border-radius: 9999px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
}

.mbvpn-window switch:not(.mbvpn-ios-switch):checked slider,
.mullvad-window switch:not(.mbvpn-ios-switch):checked slider {
    background-color: #ffffff;
}

.mbvpn-window switch:not(.mbvpn-ios-switch):disabled slider,
.mullvad-window switch:not(.mbvpn-ios-switch):disabled slider {
    background-color: #7d8899;
}

/* Primary and destructive dialog actions follow the app palette, not the desktop accent */
.mbvpn-window button.suggested-action, .mullvad-window button.suggested-action {
    background: #2a66d6;
    color: #ffffff;
    border: 1px solid #3b76e1;
    box-shadow: none;
}

.mbvpn-window button.suggested-action:hover, .mullvad-window button.suggested-action:hover {
    background: #3472e5;
    border-color: #4b83e8;
}

.mbvpn-window button.suggested-action:active, .mullvad-window button.suggested-action:active {
    background: #2257ba;
    border-color: #2f63c4;
}

.mbvpn-window button.suggested-action:disabled, .mullvad-window button.suggested-action:disabled {
    background: #18253a;
    color: #8595ac;
    border-color: #263750;
}

.mbvpn-window button.destructive-action, .mullvad-window button.destructive-action {
    background: rgba(239, 68, 68, 0.12);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.45);
    box-shadow: none;
}

.mbvpn-window button.destructive-action:hover, .mullvad-window button.destructive-action:hover {
    background: rgba(239, 68, 68, 0.2);
    color: #fecaca;
    border-color: rgba(239, 68, 68, 0.7);
}

.mbvpn-window button.destructive-action:active, .mullvad-window button.destructive-action:active {
    background: rgba(239, 68, 68, 0.3);
    color: #ffffff;
}

/* Text inputs keep the app border and focus ring instead of the desktop accent */
.mbvpn-window entry, .mullvad-window entry {
    background-color: #0e1520;
    color: #e6edf6;
    border: 1px solid #24344a;
    border-radius: 8px;
    box-shadow: none;
    outline: none;
}

.mbvpn-window entry:focus, .mullvad-window entry:focus {
    border-color: #3b76e1;
    box-shadow: inset 0 0 0 1px rgba(59, 118, 225, 0.55);
}

/* Flatter native geometry: cards drop the soft web-dashboard rounding */
.mbvpn-hero-card, .mullvad-banner {
    border-radius: 8px;
    padding: 15px 18px 14px;
}

.mbvpn-details-card, .mullvad-details-card,
.mbvpn-network-panel {
    border-radius: 6px;
}

/* Status readout: compact dark glass chip with crisp typography and subtle hairline */
.mbvpn-hero-card .mbvpn-status-sub, .mullvad-banner .mbvpn-status-sub,
.mbvpn-hero-card .mullvad-status-sub, .mullvad-banner .mullvad-status-sub {
    color: #e2e8f0;
    margin: 0;
    padding: 0 3px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.2px;
}

/* Translucent dark glass pill with balanced padding and hairline rim */
.mbvpn-status-vbox {
    background: rgba(11, 18, 32, 0.62);
    background-color: rgba(11, 18, 32, 0.62);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 9999px;
    padding: 3px 11px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05), 0 1px 4px rgba(0, 0, 0, 0.25);
}

/* Protected state tints the chip sapphire and lets it glow softly */
.mbvpn-hero-secured .mbvpn-status-vbox, .mullvad-banner-secured .mbvpn-status-vbox {
    background: rgba(14, 165, 233, 0.12);
    background-color: rgba(14, 165, 233, 0.12);
    border-color: rgba(56, 189, 248, 0.32);
    box-shadow: 0 0 8px rgba(56, 189, 248, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.07);
}

.mullvad-banner-secured .mullvad-status-sub, .mbvpn-hero-secured .mbvpn-status-sub {
    color: #e0f2fe;
}

/* Unprotected hero stays quiet steel so the protected state reads as the focus */
.mbvpn-hero-unsecured, .mullvad-banner-unsecured {
    background-color: #141c28;
    background-image: none;
    border-color: #253141;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

/* Connecting keeps the same chip, tinted blue */
.mbvpn-hero-connecting .mbvpn-status-vbox, .mullvad-banner-connecting .mbvpn-status-vbox {
    background: rgba(59, 130, 246, 0.14);
    background-color: rgba(59, 130, 246, 0.14);
    border-color: rgba(59, 130, 246, 0.36);
    box-shadow: 0 0 12px rgba(59, 130, 246, 0.16);
}

.mullvad-banner-connecting .mullvad-status-sub, .mbvpn-hero-connecting .mbvpn-status-sub {
    color: #cfe0ff;
}

/* The emblem is a status logo: no hover, no pointer affordance */
.mbvpn-shield-holder {
    background: none;
    border: none;
    box-shadow: none;
    padding: 0;
}

/* Primary connection control: refined tactile squircle */
button.mbvpn-connect-btn {
    background: none;
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 2px 6px rgba(0, 0, 0, 0.25);
    outline: none;
    padding: 0 18px;
    min-height: 36px;
    min-width: 128px;
    transition: all 160ms cubic-bezier(0.4, 0, 0.2, 1);
}

button.mbvpn-connect-btn label {
    font-size: 13.5px;
    font-weight: 700;
    letter-spacing: 0.3px;
    color: #e2e8f0;
}

button.mbvpn-connect-btn image {
    color: #94a3b8;
}

button.mbvpn-connect-btn:hover {
    background-color: rgba(255, 255, 255, 0.09);
    border-color: rgba(255, 255, 255, 0.20);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12), 0 4px 12px rgba(0, 0, 0, 0.35);
}

button.mbvpn-connect-btn:active {
    background-color: rgba(255, 255, 255, 0.12);
    box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.3);
}

/* Idle with a live subscription: transparent outline so the hero, not a slab, carries the colour */
button.mbvpn-connect-btn.accent {
    background: transparent;
    background-color: transparent;
    background-image: none;
    border: 1px solid rgba(56, 189, 248, 0.28);
    border-radius: 10px;
    box-shadow: none;
}

button.mbvpn-connect-btn.accent label,
button.mbvpn-connect-btn.accent image {
    color: #7dd3fc;
}

button.mbvpn-connect-btn.accent:hover {
    background-color: rgba(56, 189, 248, 0.08);
    background-image: none;
    border-color: rgba(56, 189, 248, 0.50);
    box-shadow: none;
}

button.mbvpn-connect-btn.accent:hover label {
    color: #bae6fd;
}

button.mbvpn-connect-btn.accent:active {
    background-color: rgba(56, 189, 248, 0.14);
    background-image: none;
    box-shadow: none;
}

/* Idle Connect only: the pointer warms the control to emerald ("this will protect me") */
button.mbvpn-connect-btn.accent.idle:hover {
    background-color: rgba(16, 185, 129, 0.10);
    background-image: none;
    border-color: rgba(52, 211, 153, 0.55);
    box-shadow: none;
}

button.mbvpn-connect-btn.accent.idle:hover label {
    color: #6ee7b7;
}

button.mbvpn-connect-btn.accent.idle:active {
    background-color: rgba(16, 185, 129, 0.16);
    border-color: rgba(52, 211, 153, 0.70);
    box-shadow: none;
}

button.mbvpn-connect-btn.accent.idle:active label {
    color: #a7f3d0;
}

/* Disconnect button: refined glassmorphic crimson squircle with subtle warm tint */
button.mbvpn-connect-btn.connected {
    background: rgba(244, 63, 94, 0.10);
    background-color: rgba(244, 63, 94, 0.10);
    border: 1px solid rgba(244, 63, 94, 0.30);
    border-radius: 10px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 2px 8px rgba(0, 0, 0, 0.30);
}

button.mbvpn-connect-btn.connected label {
    color: #fda4af;
    font-weight: 700;
}

button.mbvpn-connect-btn.connected image {
    color: #f43f5e;
    opacity: 0.95;
}

/* Connected hover: warning glow */
button.mbvpn-connect-btn.connected:hover {
    background: rgba(239, 68, 68, 0.18);
    background-color: rgba(239, 68, 68, 0.18);
    border-color: rgba(239, 68, 68, 0.55);
    box-shadow: 0 0 14px rgba(239, 68, 68, 0.28), 0 2px 8px rgba(0, 0, 0, 0.40);
}

button.mbvpn-connect-btn.connected:hover label {
    color: #ffffff;
}

button.mbvpn-connect-btn.connected:hover image {
    color: #fecdd3;
    opacity: 1;
}

button.mbvpn-connect-btn.connected:active {
    background-color: rgba(239, 68, 68, 0.28);
    border-color: rgba(239, 68, 68, 0.75);
    transform: scale(0.97);
}

button.mbvpn-connect-btn.locked {
    background-color: transparent;
    border-color: rgba(255, 255, 255, 0.12);
    box-shadow: none;
}

button.mbvpn-connect-btn:disabled {
    background-color: rgba(255, 255, 255, 0.03);
    background-image: none;
    border-color: rgba(255, 255, 255, 0.07);
    box-shadow: none;
}

button.mbvpn-connect-btn:disabled label,
button.mbvpn-connect-btn:disabled image {
    color: #8295a8;
}

/* Containerless layout: structure comes from hairlines and whitespace.
 * The hero card sits in a Gtk.Overlay on top of the WorldMapCanvas.
 * Background must be transparent so the animated map shows through.
 */
.mbvpn-hero-card, .mullvad-banner,
.mbvpn-hero-secured, .mullvad-banner-secured,
.mbvpn-hero-unsecured, .mullvad-banner-unsecured,
.mbvpn-hero-connecting, .mullvad-banner-connecting {
    background: transparent;
    background-color: transparent;
    background-image: none;
    border: none;
    border-radius: 0;
    box-shadow: none;
    padding: 6px 0 8px;
}

/* State lighting: subtle gradient wash over the transparent hero card */
.mbvpn-hero-secured, .mullvad-banner-secured {
    background-image: linear-gradient(180deg, rgba(20, 103, 224, 0.08) 0%, transparent 74%);
}

.mbvpn-hero-connecting, .mullvad-banner-connecting {
    background-image: linear-gradient(180deg, rgba(59, 130, 246, 0.06) 0%, transparent 68%);
}

.mbvpn-hero-unsecured, .mullvad-banner-unsecured {
    background-image: linear-gradient(180deg, rgba(148, 163, 184, 0.03) 0%, transparent 60%);
}

/* Location selector: clean, borderless, human-crafted interactive row */
button.mbvpn-location-card, button.mullvad-location-card {
    background: rgba(255, 255, 255, 0.035);
    background-color: rgba(255, 255, 255, 0.035);
    border: none;
    border-width: 0;
    border-color: transparent;
    outline: none;
    border-radius: 12px;
    box-shadow: none;
    padding: 10px 14px;
    transition: background-color 150ms ease, background 150ms ease;
}

button.mbvpn-location-card:hover, button.mullvad-location-card:hover {
    background: rgba(255, 255, 255, 0.065);
    background-color: rgba(255, 255, 255, 0.065);
    border: none;
    border-width: 0;
    border-color: transparent;
    outline: none;
    box-shadow: none;
}

button.mbvpn-location-card:active, button.mullvad-location-card:active {
    background: rgba(255, 255, 255, 0.045);
    background-color: rgba(255, 255, 255, 0.045);
    border: none;
    outline: none;
    box-shadow: none;
    transform: scale(0.995);
}

.mbvpn-loc-chevron {
    color: #475569;
    font-size: 13px;
    margin-right: 2px;
    transition: color 150ms ease, transform 150ms ease;
}

button.mbvpn-location-card:hover .mbvpn-loc-chevron,
button.mullvad-location-card:hover .mbvpn-loc-chevron {
    color: #94a3b8;
    transform: translateX(1.5px);
}

/* Flag presentation: natural circular emblem with soft depth */
.mbvpn-flag-frame {
    min-width: 32px;
    min-height: 32px;
    background: transparent;
    background-color: transparent;
    border: none;
    box-shadow: none;
    padding: 0;
    margin: 0;
}

.official-flag-icon {
    border-radius: 9999px;
    border: none;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.45);
}

button.mbvpn-location-card .mbvpn-country, button.mullvad-location-card .mullvad-country {
    font-size: 14px;
    font-weight: 600;
    color: #f8fafc;
    letter-spacing: 0.1px;
}

button.mbvpn-location-card .mbvpn-city, button.mullvad-location-card .mullvad-city {
    font-size: 11.5px;
    font-weight: 400;
    color: #94a3b8;
    margin-top: 1.5px;
}

.mbvpn-details-card, .mullvad-details-card {
    background: none;
    background-color: transparent;
    border: none;
    border-radius: 0;
    box-shadow: none;
    padding: 2px 0 0;
}

.mbvpn-details-header, .mullvad-details-header {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #e2e8f0;
}

.mbvpn-network-panel {
    background: none;
    background-color: transparent;
    border: none;
    border-radius: 0;
    box-shadow: none;
    padding: 8px 0 0;
}

separator.mbvpn-v-sep {
    background-color: rgba(255, 255, 255, 0.06);
    margin: 0 16px;
    min-width: 1px;
}

separator.mbvpn-h-sep {
    background-color: rgba(255, 255, 255, 0.06);
    margin: 14px 0 10px;
    min-height: 1px;
}

.mbvpn-traffic-strip {
    padding-top: 2px;
    padding-bottom: 2px;
}

.mbvpn-details-subtle, .mullvad-details-subtle {
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: 0.4px;
    color: #e2e8f0;
}

.mbvpn-traffic-down-arrow {
    color: #10b981;
    font-weight: 800;
    font-size: 11px;
    margin-right: 4px;
}

.mbvpn-traffic-up-arrow {
    color: #38bdf8;
    font-weight: 800;
    font-size: 11px;
    margin-left: 12px;
    margin-right: 4px;
}

.mbvpn-details-val, .mullvad-details-val {
    font-size: 13.5px;
    font-weight: 700;
    color: #f8fafc;
    letter-spacing: 0.5px;
}

switch.mbvpn-ios-switch {
    background-color: rgba(255, 255, 255, 0.16);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 9999px;
    min-width: 44px;
    min-height: 24px;
    outline: none;
    transition: all 180ms cubic-bezier(0.4, 0, 0.2, 1);
}

switch.mbvpn-ios-switch:checked {
    background: #0ca987;
    border-color: rgba(16, 185, 129, 0.4);
    box-shadow: 0 0 10px rgba(16, 185, 129, 0.35);
}

switch.mbvpn-ios-switch slider {
    background-color: #cbd5e1;
    border-radius: 9999px;
    min-width: 18px;
    min-height: 18px;
    outline: none;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.45);
    transition: all 180ms cubic-bezier(0.4, 0, 0.2, 1);
}

switch.mbvpn-ios-switch:checked slider {
    background-color: #ffffff;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.5);
}

/* ------------------------------------------------------------------
   Security & Privacy summary — clean, quiet, minimal typography
   ------------------------------------------------------------------ */
.mbvpn-details-card, .mullvad-details-card {
    background: transparent;
    border: none;
    border-radius: 0;
    box-shadow: none;
    padding: 0;
}

.mbvpn-details-header, .mullvad-details-header {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #cbd5e1;
    padding: 2px 0;
}

.mbvpn-proto-badge {
    background: none;
    border: none;
    border-radius: 0;
    padding: 2px 0 3px 0;
    min-height: 18px;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.3px;
    color: #64748b;
}

.mbvpn-network-panel {
    background: none;
    background-color: transparent;
    border: none;
    border-radius: 0;
    box-shadow: none;
    padding: 12px 0 0;
}

/* Micro-labels */
.mbvpn-panel-label, .mbvpn-details-subtle {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.9px;
    text-transform: uppercase;
    color: #64748b;
    padding: 1px 0;
}

.mbvpn-time-title {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.9px;
    text-transform: uppercase;
    color: #64748b;
    padding: 1px 0;
}

.mbvpn-time-total {
    color: #f1f5f9;
    font-size: 20px;
    font-weight: 650;
    letter-spacing: -0.3px;
    padding: 0;
}

.mbvpn-time-caption {
    color: #64748b;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.2px;
    padding: 1px 0;
}

.mbvpn-panel-sub {
    font-size: 12px;
    font-weight: 600;
    color: #94a3b8;
    padding: 1px 0;
}

.mbvpn-panel-sub.disabled {
    color: #64748b;
}

.mbvpn-panel-sub.armed {
    color: #fbbf24;
}

.mbvpn-panel-sub.active {
    color: #34d399;
}

.mbvpn-ks-hint {
    color: #64748b;
    font-size: 9.5px;
    font-weight: 400;
    letter-spacing: 0.1px;
    padding: 0 0 2px 0;
    margin-top: 1px;
    min-height: 15px;
}

separator.mbvpn-h-sep {
    background-color: rgba(255, 255, 255, 0.055);
    margin: 8px 0 7px;
    min-height: 1px;
}

.mbvpn-traffic-strip {
    padding: 3px 0 1px 0;
    min-height: 20px;
}

.mbvpn-details-val, .mullvad-details-val, .mbvpn-traffic-val {
    font-size: 12px;
    font-weight: 600;
    color: #e2e8f0;
    letter-spacing: 0.2px;
    font-variant-numeric: tabular-nums;
    font-feature-settings: "tnum" 1;
    padding: 0;
}

.mbvpn-traffic-down-arrow {
    color: #34d399;
    font-weight: 800;
    font-size: 13px;
    margin-right: 1px;
    padding: 0;
}

.mbvpn-traffic-up-arrow {
    color: #38bdf8;
    font-weight: 800;
    font-size: 13px;
    margin-right: 1px;
    padding: 0;
}

""".replace("__ASSETS_DIR__", str(ASSETS_DIR))


class BrandShieldWidget(Gtk.Overlay):
    """
    Enterprise-grade Malwarebytes Shield status display.
    Features authentic vector shield rendering, calm ambient illumination,
    and a smooth, high-precision circular indeterminate progress indicator
    during connection transitions without gimmicky sci-fi artifacts.
    """
    def __init__(self, protected_path: str, unprotected_path: str, size: int = 96, emblem_ratio: float = 0.60):
        super().__init__()
        self.size = size
        self.set_size_request(size, size)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)

        self.protected_path = protected_path
        self.unprotected_path = unprotected_path

        # Ambient backdrop and clean connecting progress canvas
        self.canvas = Gtk.DrawingArea()
        self.canvas.set_content_width(size)
        self.canvas.set_content_height(size)
        self.canvas.set_draw_func(self._draw_canvas)
        self.set_child(self.canvas)

        # Central Vector Shield Image
        self.img_shield = Gtk.Image()
        self.img_shield.set_pixel_size(int(size * emblem_ratio))
        self.img_shield.set_halign(Gtk.Align.CENTER)
        self.img_shield.set_valign(Gtk.Align.CENTER)
        if os.path.exists(self.unprotected_path):
            self.img_shield.set_from_file(self.unprotected_path)
        else:
            self.img_shield.set_from_icon_name("channel-insecure-symbolic")
        self.add_overlay(self.img_shield)

        self.state = "unprotected"  # "connecting", "disconnecting", "protected", "unprotected"
        self.angle = 0.0
        self.pulse = 0.0
        self.timer_id = None

    def start_animation(self, mode: str = "connecting"):
        self.state = mode
        if os.path.exists(self.unprotected_path):
            self.img_shield.set_from_file(self.unprotected_path)
        self.img_shield.set_opacity(1.0)
        if self.timer_id is None:
            self.timer_id = GLib.timeout_add(16, self._on_tick)
        self.canvas.queue_draw()

    def set_mode(self, mode: str):
        self.state = mode
        self.img_shield.set_opacity(1.0)
        if mode == "protected":
            if os.path.exists(self.protected_path):
                self.img_shield.set_from_file(self.protected_path)
            else:
                self.img_shield.set_from_icon_name("channel-secure-symbolic")
        elif mode in ("unprotected", "disconnecting"):
            if os.path.exists(self.unprotected_path):
                self.img_shield.set_from_file(self.unprotected_path)
            else:
                self.img_shield.set_from_icon_name("channel-insecure-symbolic")

        if mode in ("protected", "unprotected") and self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
        self.canvas.queue_draw()

    def _on_tick(self):
        if self.state == "connecting":
            # Steady cruise with a faint sway so the orbit never reads as a mechanical spinner
            speed = 0.042 + 0.006 * math.sin(self.pulse * 0.7)
            self.angle = (self.angle + speed) % (2 * math.pi)
            self.pulse = (self.pulse + 0.026) % (2 * math.pi)
            # Barely-there breathe on the emblem itself
            if hasattr(self, "img_shield"):
                self.img_shield.set_opacity(0.93 + 0.07 * (0.5 + 0.5 * math.sin(self.pulse)))
        else:
            self.angle = (self.angle + 0.05) % (2 * math.pi)
            self.pulse = (self.pulse + 0.03) % (2 * math.pi)
        self.canvas.queue_draw()
        return True

    def _stroke_comet(self, cr, cx, cy, radius, head, scale, rgb,
                      span=2.5, peak_alpha=0.95, max_width=2.6):
        """Draw a soft comet trail: overlapping arc segments that fade toward the tail."""
        steps = 64
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        for i in range(steps):
            t = i / (steps - 1)  # 0 = tail, 1 = head
            alpha = peak_alpha * (t ** 2.5)
            if alpha < 0.006:
                continue
            start = head - span + span * t
            cr.set_source_rgba(rgb[0], rgb[1], rgb[2], alpha)
            cr.set_line_width((0.8 + (max_width - 0.8) * t) * scale)
            # Overlap the segments a little so no banding shows between them
            cr.arc(cx, cy, radius, start, start + (span / steps) * 2.1)
            cr.stroke()

        # Leading tip: small radial bloom plus a crisp bright dot
        hx = cx + radius * math.cos(head)
        hy = cy + radius * math.sin(head)
        glow = cairo.RadialGradient(hx, hy, 0.0, hx, hy, 8.0 * scale)
        glow.add_color_stop_rgba(
            0.0,
            min(1.0, rgb[0] + 0.55),
            min(1.0, rgb[1] + 0.30),
            min(1.0, rgb[2] + 0.05),
            0.50,
        )
        glow.add_color_stop_rgba(0.45, rgb[0], rgb[1], rgb[2], 0.18)
        glow.add_color_stop_rgba(1.0, rgb[0], rgb[1], rgb[2], 0.0)
        cr.set_source(glow)
        cr.arc(hx, hy, 8.0 * scale, 0, 2 * math.pi)
        cr.fill()

        cr.set_source_rgba(
            min(1.0, rgb[0] + 0.60),
            min(1.0, rgb[1] + 0.35),
            min(1.0, rgb[2] + 0.10),
            0.95,
        )
        cr.arc(hx, hy, 1.6 * scale, 0, 2 * math.pi)
        cr.fill()

    def _draw_canvas(self, area, cr, w, h):
        cx, cy = w / 2.0, h / 2.0
        # Radii and strokes are proportional so the emblem scales cleanly
        base = min(w, h) / 2.0
        scale = base / 42.0
        ring = base * 0.94
        outer_rim = base * 0.90
        aura = base * 1.0

        if self.state == "connecting":
            breathe = 0.5 + 0.5 * math.sin(self.pulse)
            # Wide sapphire halo that breathes while the tunnel is negotiated
            rg = cairo.RadialGradient(cx, cy, base * 0.10, cx, cy, aura)
            rg.add_color_stop_rgba(0.0, 0.15, 0.58, 1.0, 0.14 + 0.10 * breathe)
            rg.add_color_stop_rgba(0.55, 0.15, 0.58, 1.0, 0.06 + 0.05 * breathe)
            rg.add_color_stop_rgba(1.0, 0.15, 0.58, 1.0, 0.0)
            cr.set_source(rg)
            cr.arc(cx, cy, aura, 0, 2 * math.pi)
            cr.fill()

            # The orbit breathes in and out with the halo instead of sitting on a fixed radius
            orbit = ring + 0.6 * scale * math.sin(self.pulse)

            # Quiet track the comet travels along
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.055)
            cr.set_line_width(1.5 * scale)
            cr.arc(cx, cy, orbit, 0, 2 * math.pi)
            cr.stroke()

            # Smooth comet: a long fading trail with a bright leading tip
            self._stroke_comet(cr, cx, cy, orbit, self.angle, scale, (0.18, 0.66, 1.0))

        elif self.state == "disconnecting":
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.055)
            cr.set_line_width(1.5 * scale)
            cr.arc(cx, cy, ring, 0, 2 * math.pi)
            cr.stroke()

            # Amber counterpart, counter-rotating to read as teardown
            self._stroke_comet(cr, cx, cy, ring, -self.angle, scale, (0.96, 0.63, 0.18),
                               span=1.9, peak_alpha=0.75)

        elif self.state == "protected":
            # Layered sapphire aura: a wide ambient wash plus a tight core glow
            rg = cairo.RadialGradient(cx, cy, base * 0.10, cx, cy, aura)
            rg.add_color_stop_rgba(0.0, 0.10, 0.55, 1.0, 0.34)
            rg.add_color_stop_rgba(0.45, 0.14, 0.62, 0.98, 0.16)
            rg.add_color_stop_rgba(0.75, 0.14, 0.62, 0.98, 0.06)
            rg.add_color_stop_rgba(1.0, 0.10, 0.55, 1.0, 0.0)
            cr.set_source(rg)
            cr.arc(cx, cy, aura, 0, 2 * math.pi)
            cr.fill()

            # Sapphire containment ring: the visual signature of an active tunnel
            cr.set_source_rgba(0.25, 0.66, 1.0, 0.55)
            cr.set_line_width(1.8 * scale)
            cr.arc(cx, cy, outer_rim, 0, 2 * math.pi)
            cr.stroke()

            # Hairline glass rim just outside it for depth
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.12)
            cr.set_line_width(1.2 * scale)
            cr.arc(cx, cy, ring, 0, 2 * math.pi)
            cr.stroke()

        elif self.state == "unprotected":
            # Clean floating presentation: no ring, no glow, no artificial circle
            pass


class ProtectionChart(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.set_content_width(150)
        self.set_content_height(46)
        self.set_size_request(110, 46)
        self.daily_seconds = [0.0] * 7
        self.set_draw_func(self._draw)

    def set_daily_seconds(self, values):
        self.daily_seconds = list(values)
        self.queue_draw()

    def _draw(self, _area, cr, width, height):
        day_labels = ("S", "M", "T", "W", "T", "F", "S")
        chart_height = max(12, height - 16)
        baseline = chart_height
        cell_width = width / 7
        maximum = max(max(self.daily_seconds, default=0), 3600)

        # Baseline rule
        cr.set_line_width(1)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.10)
        cr.move_to(0, baseline + 0.5)
        cr.line_to(width, baseline + 0.5)
        cr.stroke()

        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(10.0)
        today_idx = (date.today().weekday() + 1) % 7

        for index, seconds in enumerate(self.daily_seconds):
            bar_width = min(8.5, cell_width * 0.48)
            x = index * cell_width + (cell_width - bar_width) / 2

            if seconds > 0:
                bar_height = max(6, (seconds / maximum) * (chart_height - 4))
                r = min(bar_width / 2.0, 4.0)
                y = baseline - bar_height

                # Draw smooth pill bar with rounded top
                cr.new_sub_path()
                cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
                cr.arc(x + bar_width - r, y + r, r, 1.5 * math.pi, 2 * math.pi)
                cr.line_to(x + bar_width, baseline)
                cr.line_to(x, baseline)
                cr.close_path()

                if index == today_idx:
                    cr.set_source_rgba(0.22, 0.82, 1.0, 1.0)
                else:
                    cr.set_source_rgba(0.32, 0.64, 0.96, 0.75)
                cr.fill()
            else:
                # Inactive day: calm rounded baseline stub
                stub_w = min(6.0, cell_width * 0.38)
                sx = index * cell_width + (cell_width - stub_w) / 2
                cr.set_line_width(2.5)
                cr.set_line_cap(cairo.LINE_CAP_ROUND)
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.18)
                cr.move_to(sx, baseline - 1.0)
                cr.line_to(sx + stub_w, baseline - 1.0)
                cr.stroke()
                cr.set_line_cap(cairo.LINE_CAP_BUTT)

            if index == today_idx:
                cr.set_source_rgba(0.22, 0.82, 1.0, 1.0)
            else:
                cr.set_source_rgba(0.68, 0.78, 0.90, 0.88)
            extents = cr.text_extents(day_labels[index])
            cr.move_to(index * cell_width + (cell_width - extents.width) / 2, height - 2)
            cr.show_text(day_labels[index])


# Backward compatibility alias
CyberShieldWidget = BrandShieldWidget


class WorldMapCanvas(Gtk.DrawingArea):
    """Subtle animated world map background for the hero card.

    Renders an equirectangular atlas PNG with:
    - Seamless horizontal wrapping (draw at base_x, base_x±atlas_w)
    - Smooth eased panning toward the active server's geographic coordinates
    - Animated radar-pulse beacon at the target location
    - Dark gradient base and radial vignette for text contrast
    """

    ATLAS_W = 1162
    ATLAS_H = 560
    # Card geometry (must match hero card padding/margin)
    CARD_W = 344
    CARD_H = 195

    def __init__(self):
        super().__init__()
        self.set_content_width(self.CARD_W)
        self.set_content_height(self.CARD_H)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_draw_func(self._draw)

        # Atlas surface (loaded lazily)
        self._atlas_surf = None
        self._atlas_loaded = False

        # Coordinate state
        self._target_x = self.ATLAS_W * 0.5  # default: center of map
        self._target_y = self.ATLAS_H * 0.28  # default: Europe-ish
        self._current_x = self._target_x
        self._current_y = self._target_y
        self._show_beacon = False
        self._state = "unprotected"  # "protected", "connecting", "unprotected"

        # Animation state
        self._beacon_phase = 0.0
        self._timer_id = None

        # Coordinate lookup table: built once from servers.json
        self._coords_db: Dict[str, tuple] = {}
        self._build_coords_db()

    def _build_coords_db(self):
        """Build a lookup dictionary mapping server hostnames, city codes, city
        names, and country codes/names to (lat, lon) tuples."""
        servers_file = Path(os.path.expanduser("~/.config/mbvpn/servers.json"))
        if not servers_file.exists():
            return
        try:
            with open(servers_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for c in data.get("countries", []):
                c_code = c.get("code", "").lower()
                c_name = c.get("name", "").lower()
                for ct in c.get("cities", []):
                    ct_code = ct.get("code", "").lower()
                    ct_name = ct.get("name", "").lower()
                    lat = ct.get("latitude", 0.0)
                    lon = ct.get("longitude", 0.0)
                    self._coords_db[ct_code] = (lat, lon)
                    self._coords_db[ct_name] = (lat, lon)
                    if c_code not in self._coords_db:
                        self._coords_db[c_code] = (lat, lon)
                    if c_name not in self._coords_db:
                        self._coords_db[c_name] = (lat, lon)
                    for s in ct.get("servers", []):
                        h = s.get("hostname", "").split(".")[0].lower()
                        self._coords_db[h] = (lat, lon)
        except Exception:
            pass

    def _load_atlas(self):
        """Load the atlas PNG surface once."""
        if self._atlas_loaded:
            return
        self._atlas_loaded = True
        atlas_path = str(ASSETS_DIR / "bg_vpn_connected_atlas_loud.png")
        if os.path.exists(atlas_path):
            try:
                self._atlas_surf = cairo.ImageSurface.create_from_png(atlas_path)
            except Exception:
                self._atlas_surf = None

    def _latlon_to_pixel(self, lat: float, lon: float) -> tuple:
        """Convert lat/lon to pixel coordinates on the equirectangular atlas."""
        px = (lon + 180.0) / 360.0 * self.ATLAS_W
        py = (90.0 - lat) / 180.0 * self.ATLAS_H
        return px, py

    def set_target(self, server: str = "", city: str = "", country: str = ""):
        """Set the map's target coordinates from a server/city/country identifier."""
        lat, lon = None, None
        for key in [server, city, country]:
            k = key.lower().strip() if key else ""
            if k and k in self._coords_db:
                lat, lon = self._coords_db[k]
                break
        if lat is not None and lon is not None:
            self._target_x, self._target_y = self._latlon_to_pixel(lat, lon)

    def set_state(self, state: str):
        """Set visual state: 'protected', 'connecting', or 'unprotected'."""
        self._state = state
        self._show_beacon = state in ("protected", "connecting")
        if state in ("protected", "connecting"):
            self._start_animation()
        elif self._timer_id is not None:
            # Keep animating briefly for the pan to settle
            pass
        self.queue_draw()

    def _start_animation(self):
        if self._timer_id is None:
            self._timer_id = GLib.timeout_add(16, self._on_tick)

    def _on_tick(self):
        # Smooth easing toward target
        dx = self._target_x - self._current_x
        dy = self._target_y - self._current_y
        self._current_x += dx * 0.06
        self._current_y += dy * 0.06

        self._beacon_phase = (self._beacon_phase + 0.04) % (2 * math.pi)
        self.queue_draw()

        # Stop ticking if settled and unprotected
        if self._state == "unprotected" and abs(dx) < 0.5 and abs(dy) < 0.5:
            self._timer_id = None
            return False
        return True

    def _draw(self, area, cr, w, h):
        self._load_atlas()

        # Rounded rectangle clip matching the reference card geometry
        r = 14.0
        cr.save()
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi / 2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi / 2)
        cr.arc(r, h - r, r, math.pi / 2, math.pi)
        cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.clip()

        # --- Dark gradient background ---
        rg = cairo.LinearGradient(0, 0, 0, h)
        rg.add_color_stop_rgb(0.0, 0.063, 0.110, 0.184)  # #101c2f
        rg.add_color_stop_rgb(1.0, 0.040, 0.071, 0.114)  # #0a121d
        cr.set_source(rg)
        cr.paint()

        if self._atlas_surf is not None:
            atlas_w = self._atlas_surf.get_width()
            atlas_h = self._atlas_surf.get_height()

            # Scale atlas to fit card height with some room
            scale = h / atlas_h * 1.5
            map_w = atlas_w * scale

            # Center of card where the shield sits
            cx, cy = w / 2.0, h * 0.36

            # Calculate offset to center current position behind the shield
            off_x = cx - self._current_x * scale
            off_y = cy - self._current_y * scale
            # Clamp vertical so map doesn't scroll past edges
            off_y = max(h - atlas_h * scale, min(0, off_y))

            # Determine alpha based on state
            if self._state == "protected":
                atlas_alpha = 0.16
            elif self._state == "connecting":
                atlas_alpha = 0.12
            else:
                atlas_alpha = 0.07

            # Draw atlas with seamless horizontal wrapping
            cr.save()
            cr.scale(scale, scale)
            base_x = (off_x / scale) % atlas_w
            if base_x > 0:
                base_x -= atlas_w
            for shift in [base_x, base_x + atlas_w, base_x + 2 * atlas_w]:
                cr.set_source_surface(self._atlas_surf, shift, off_y / scale)
                cr.paint_with_alpha(atlas_alpha)
            cr.restore()

            # --- Radial vignette for contrast ---
            vig = cairo.RadialGradient(cx, cy, 20, cx, cy, max(w, h) * 0.7)
            vig.add_color_stop_rgba(0.0, 0.05, 0.09, 0.16, 0.20)
            vig.add_color_stop_rgba(0.5, 0.05, 0.09, 0.16, 0.40)
            vig.add_color_stop_rgba(1.0, 0.04, 0.07, 0.11, 0.70)
            cr.set_source(vig)
            cr.paint()

            # --- Radar beacon at target location ---
            if self._show_beacon:
                bx = off_x + self._current_x * scale
                by = off_y + self._current_y * scale
                # Keep beacon within card bounds
                if 0 <= bx <= w and 0 <= by <= h:
                    pulse = (1.0 + math.sin(self._beacon_phase * 2.0)) * 0.5

                    # Outer ripple ring
                    ripple_r = 8.0 + pulse * 14.0
                    ripple_alpha = 0.35 * (1.0 - pulse)
                    cr.set_source_rgba(0.22, 0.74, 0.97, ripple_alpha)
                    cr.set_line_width(1.2)
                    cr.arc(bx, by, ripple_r, 0, 2 * math.pi)
                    cr.stroke()

                    # Second ripple (offset phase)
                    pulse2 = (1.0 + math.sin(self._beacon_phase * 2.0 + math.pi)) * 0.5
                    ripple_r2 = 8.0 + pulse2 * 10.0
                    ripple_alpha2 = 0.25 * (1.0 - pulse2)
                    cr.set_source_rgba(0.22, 0.74, 0.97, ripple_alpha2)
                    cr.set_line_width(0.8)
                    cr.arc(bx, by, ripple_r2, 0, 2 * math.pi)
                    cr.stroke()

                    # Core dot
                    cr.set_source_rgba(0.22, 0.74, 0.97, 0.90)
                    cr.arc(bx, by, 3.0, 0, 2 * math.pi)
                    cr.fill()

                    # Bright center
                    cr.set_source_rgba(0.72, 0.92, 1.0, 0.85)
                    cr.arc(bx, by, 1.2, 0, 2 * math.pi)
                    cr.fill()

        cr.restore()  # restore clipping

        # Draw subtle card outline border
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi / 2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi / 2)
        cr.arc(r, h - r, r, math.pi / 2, math.pi)
        cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
        if self._state == "protected":
            cr.set_source_rgba(0.22, 0.74, 0.97, 0.22)
        elif self._state == "connecting":
            cr.set_source_rgba(0.22, 0.74, 0.97, 0.16)
        else:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.08)
        cr.set_line_width(1.0)
        cr.stroke()


class MbVpnWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_css_class("mullvad-window")
        self.add_css_class("mbvpn-window")
        self.set_default_size(380, 545)
        self.set_size_request(380, 545)
        self.set_resizable(False)
        self.set_title("MalwarebytesVPN")

        # Register application icon search paths
        display = Gdk.Display.get_default()
        if display:
            theme = Gtk.IconTheme.get_for_display(display)
            theme.add_search_path(str(ASSETS_DIR))
            theme.add_search_path(str(APP_DIR))
        self.set_icon_name("mbvpn")

        self.backend = MbVpnBackend()
        self.is_busy = False
        self.is_connected = False
        self.should_be_connected = False
        self._cancel_connect_requested = False

        self.settings_file = Path.home() / ".config" / "mbvpn" / "gui_settings.json"
        self.settings = self._load_settings()
        if not isinstance(self.settings.get("protection_daily"), dict):
            self.settings["protection_daily"] = {}
        self._protection_last_sample = None
        self._protection_last_saved_minute = None

        # Ensure killswitch and split tunneling bypass matches setting on startup
        def sync_killswitch():
            try:
                if not self.settings.get("hard_kill_switch", False):
                    self.backend.apply_split_tunneling(
                        self.settings.get("bypass_apps", []),
                        self.settings.get("bypass_antigravity", True),
                    )
                if self.settings.get("kill_switch"):
                    self.backend.enable_killswitch(
                        bypass_apps=self.settings.get("bypass_apps", []),
                        bypass_antigravity=self.settings.get("bypass_antigravity", True),
                        hard=self.settings.get("hard_kill_switch", False),
                    )
                else:
                    self.backend.disable_killswitch()
            except Exception:
                pass
        threading.Thread(target=sync_killswitch, daemon=True).start()

        # Current selection: default to US (Auto)
        self.selected_target = self.settings.get("last_target", "us")
        self.selected_label = self.settings.get("last_label", "United States")
        self.selected_flag = self.settings.get("last_flag", "🇺🇸")
        self.selected_sub = self._clean_sub_text(self.settings.get("last_sub", "Optimal Server"))

        self._load_css()
        self._build_ui()
        self._start_refresh_loop()

        # Initialize StatusNotifierItem System Tray
        self.tray = init_tray(
            on_activate=self._toggle_window_visibility,
            on_toggle_vpn=lambda: self._on_toggle_clicked(None),
            on_connect_target=self._connect_from_tray,
            on_quit=self._quit_application,
            get_recent_servers=self._get_recent_servers,
        )

        # Handle window close: minimize to tray instead of quitting if enabled
        self.connect("close-request", self._on_close_request)

        if hasattr(self, "world_map") and hasattr(self, "selected_target"):
            self.world_map.set_target(server=self.selected_target)

        self.refresh_async()

        # Auto-connect if enabled
        if self.settings.get("auto_connect", False):
            GLib.timeout_add_seconds(2, self._check_startup_autoconnect)

    def _get_recent_servers(self) -> List[Dict[str, str]]:
        recent = self.settings.get("recent_servers", [])
        if not recent:
            return [
                {"target": "us-lax-2", "label": "Los Angeles, CA", "flag": "🇺🇸", "sub": "Optimal Server"},
                {"target": "de-fra-1", "label": "Frankfurt am Main", "flag": "🇩🇪", "sub": "Optimal Server"},
                {"target": "be-bru-1", "label": "Brussels", "flag": "🇧🇪", "sub": "Optimal Server"},
            ]
        return recent

    def _add_recent_server(self, target: str, label: str, flag: str, sub: str):
        recent = self.settings.get("recent_servers", [])
        recent = [r for r in recent if r.get("target") != target]
        recent.insert(0, {"target": target, "label": label, "flag": flag, "sub": sub})
        self.settings["recent_servers"] = recent[:5]
        self._save_settings()
        if hasattr(self, "tray") and self.tray:
            self.tray._rebuild_menu()

    def _connect_from_tray(self, target: str, label: str, flag: str, sub: str):
        self.selected_target = target
        self.selected_label = label
        self.selected_flag = flag
        self.selected_sub = sub
        self.lbl_flag.set_label(self.selected_flag)
        self.lbl_loc_name.set_label(self.selected_label)
        self.lbl_loc_sub.set_label(self.selected_sub)
        self._update_flag_icon()
        if hasattr(self, "world_map"):
            self.world_map.set_target(server=target)
        self._add_recent_server(target, label, flag, sub)
        self._connect_vpn()

    def _toggle_window_visibility(self):
        if self.is_visible():
            self.set_visible(False)
        else:
            self.set_visible(True)
            self.present()

    def _on_close_request(self, _):
        if self.settings.get("minimize_to_tray", True):
            self.set_visible(False)
            return True
        return False

    def _quit_application(self):
        app = self.get_application()
        if app:
            app.quit()
        else:
            sys.exit(0)

    def _clean_sub_text(self, sub: str) -> str:
        """Sanitizes subtitle labels by removing internal debug strings and formatting cleanly."""
        if not sub:
            return "Optimal Server"
        s = sub.split(" • ")[0].split(" · ")[0].strip()
        if s.startswith("Country Auto") or s.startswith("City:"):
            return "Optimal Server"
        return s or "Optimal Server"

    def _load_settings(self) -> dict:
        defaults = {
            "kill_switch": False,
            "hard_kill_switch": False,
            "dns_leak_shield": True,
            "mac_randomization": True,
            "auto_reconnect": True,
            "auto_connect": False,
            "minimize_to_tray": True,
            "bypass_antigravity": True,
            "bypass_apps": [shutil.which("agy") or os.path.expanduser("~/.local/bin/agy"), shutil.which("foot") or "/usr/bin/foot"],
            "last_target": "us",
            "last_label": "United States",
            "last_flag": "🇺🇸",
            "last_sub": "Optimal Server",
        }
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    defaults.update(data)
            except Exception:
                pass
        if "last_sub" in defaults:
            defaults["last_sub"] = self._clean_sub_text(defaults["last_sub"])
        if "recent_servers" in defaults and isinstance(defaults["recent_servers"], list):
            for r in defaults["recent_servers"]:
                if isinstance(r, dict) and "sub" in r:
                    r["sub"] = self._clean_sub_text(r["sub"])
        return defaults

    def _save_settings(self):
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print("Failed to save settings:", e)

    def _check_startup_autoconnect(self):
        if not self.is_connected and not self.is_busy:
            if not self.backend.is_logged_in():
                return False
            self._connect_vpn()
        return False

    def _load_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CUSTOM_CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(main_box)

        # 1. Malwarebytes Modern HeaderBar
        header = Adw.HeaderBar()
        header.add_css_class("flat")
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        header.set_centering_policy(Adw.CenteringPolicy.STRICT)

        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_box.set_halign(Gtk.Align.CENTER)
        title_box.set_valign(Gtk.Align.CENTER)

        logo_path = str(ASSETS_DIR / "malwarebytes_logo.svg")
        if os.path.exists(logo_path):
            logo_pic = Gtk.Picture.new_for_filename(logo_path)
            logo_pic.set_can_shrink(True)
            logo_pic.set_size_request(80, 11)
            title_box.append(logo_pic)
        else:
            lbl_mwb = Gtk.Label(label="MALWAREBYTES")
            lbl_mwb.add_css_class("mullvad-header-title")
            title_box.append(lbl_mwb)

        badge_vpn = Gtk.Label(label="VPN")
        badge_vpn.add_css_class("mbvpn-header-badge")
        badge_vpn.set_valign(Gtk.Align.CENTER)
        title_box.append(badge_vpn)

        header.set_title_widget(title_box)
        self.title_widget = Adw.WindowTitle(title="MalwarebytesVPN")

        left_group = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        left_group.add_css_class("mbvpn-header-group")
        left_group.set_margin_start(8)

        self.btn_account = Gtk.Button(icon_name="avatar-default-symbolic")
        self.btn_account.add_css_class("flat")
        self.btn_account.set_tooltip_text("Subscription and Account")
        self.btn_account.connect("clicked", lambda _: self._show_account_dialog())
        left_group.append(self.btn_account)

        self.btn_refresh = Gtk.Button(icon_name="view-refresh-symbolic")
        self.btn_refresh.add_css_class("flat")
        self.btn_refresh.set_tooltip_text("Refresh Network Status")
        self.btn_refresh.connect("clicked", lambda _: self.refresh_async())
        left_group.append(self.btn_refresh)
        header.pack_start(left_group)

        self.btn_settings = Gtk.Button(icon_name="emblem-system-symbolic")
        self.btn_settings.add_css_class("flat")
        self.btn_settings.set_tooltip_text("Settings & Preferences")
        self.btn_settings.connect("clicked", lambda _: self._show_settings_dialog())

        self.btn_close = Gtk.Button()
        img_close = Gtk.Image.new_from_icon_name("window-close-symbolic")
        img_close.set_pixel_size(12)
        self.btn_close.set_child(img_close)
        self.btn_close.add_css_class("flat")
        self.btn_close.add_css_class("mbvpn-btn-close")
        self.btn_close.set_valign(Gtk.Align.CENTER)
        self.btn_close.set_tooltip_text(None)
        self.btn_close.connect("clicked", lambda _: self.close())

        right_group = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        right_group.add_css_class("mbvpn-header-group")
        right_group.set_margin_end(8)
        right_group.append(self.btn_settings)
        right_group.append(self.btn_close)
        header.pack_end(right_group)

        main_box.append(header)

        # 2. Toast Overlay
        self.toast_overlay = Adw.ToastOverlay()
        main_box.append(self.toast_overlay)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=11)
        content.set_valign(Gtk.Align.START)
        content.set_margin_top(6)
        content.set_margin_bottom(12)
        content.set_margin_start(18)
        content.set_margin_end(18)
        self.toast_overlay.set_child(content)

        # Capabilities warning banner
        self.banner_cap = Adw.Banner()
        self.banner_cap.set_title("Network capability needed for VPN and Kill Switch.")
        self.banner_cap.set_button_label("Fix Permissions")
        self.banner_cap.connect("button-clicked", lambda _: self._fix_capabilities())
        content.append(self.banner_cap)

        # 1. Top Status Banner (Hero Card)
        content.append(self._build_hero_section())

        # 2. Location Selector Card
        content.append(self._build_location_selector_card())

        # 3. Connection Details Card
        content.append(self._build_bottom_details_section())
        self.telemetry_box = Gtk.Box()

        # Initialize security preferences
        self._build_security_preferences_section()

    def _build_hero_section(self) -> Gtk.Widget:
        """Malwarebytes status block with animated world map background."""
        # --- World Map Background ---
        self.world_map = WorldMapCanvas()

        # --- Hero Overlay: map underneath, controls on top ---
        self.hero_overlay = Gtk.Overlay()
        self.hero_overlay.set_child(self.world_map)

        self.banner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.banner_box.add_css_class("mullvad-banner")
        self.banner_box.add_css_class("mbvpn-hero-card")
        self.banner_box.add_css_class("mullvad-banner-unsecured")
        self.banner_box.set_halign(Gtk.Align.FILL)
        self.banner_box.set_valign(Gtk.Align.FILL)

        shield_prot = str(ASSETS_DIR / "shield_protected.svg")
        shield_unprot = str(ASSETS_DIR / "shield_unprotected.svg")
        self.cyber_shield = CyberShieldWidget(shield_prot, shield_unprot, size=96, emblem_ratio=0.66)
        self.img_shield = self.cyber_shield.img_shield

        # Spinner maintained for backward compatibility (invisible)
        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)

        is_auth = self.backend.is_logged_in()

        # The Malwarebytes emblem is a status logo: it carries no click affordance
        self.shield_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.shield_box.add_css_class("mbvpn-shield-holder")
        self.shield_box.set_halign(Gtk.Align.CENTER)
        self.shield_box.set_valign(Gtk.Align.CENTER)
        self.shield_box.append(self.cyber_shield)
        self.banner_box.append(self.shield_box)

        self.lbl_status_desc = Gtk.Label()
        self.lbl_status_desc.add_css_class("mullvad-status-sub")
        self.lbl_status_desc.set_halign(Gtk.Align.CENTER)
        self.lbl_status_desc.set_valign(Gtk.Align.CENTER)
        self.lbl_status_desc.set_xalign(0.5)
        self.lbl_status_desc.set_justify(Gtk.Justification.CENTER)
        # Single line with adequate height: status text changes must never reflow the dashboard or clip descenders
        self.lbl_status_desc.set_wrap(False)
        self.lbl_status_desc.set_size_request(-1, 20)
        self._set_status_message("VPN is off" if is_auth else "Sign in to activate VPN", "#fb7185")

        chip_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        chip_row.add_css_class("mbvpn-status-vbox")
        chip_row.set_halign(Gtk.Align.CENTER)
        chip_row.set_valign(Gtk.Align.CENTER)
        chip_row.append(self.lbl_status_desc)
        self.status_vbox = chip_row
        self.banner_box.append(chip_row)

        # Primary connection control, centred beneath the status readout
        self.btn_connect = Gtk.Button()
        self.btn_connect.add_css_class("mbvpn-connect-btn")
        self.btn_connect.add_css_class("accent" if is_auth else "locked")
        self.btn_connect.set_halign(Gtk.Align.CENTER)
        self.btn_connect.set_valign(Gtk.Align.CENTER)
        self.btn_connect.connect("clicked", self._on_toggle_clicked)

        connect_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        connect_content.set_halign(Gtk.Align.CENTER)
        connect_content.set_valign(Gtk.Align.CENTER)
        self.img_connect_icon = Gtk.Image.new_from_icon_name("system-shutdown-symbolic" if is_auth else "avatar-default-symbolic")
        self.img_connect_icon.set_pixel_size(15)
        self.img_connect_icon.set_valign(Gtk.Align.CENTER)
        # Text-only control: the label carries the action, centred on the button
        self.img_connect_icon.set_visible(False)

        self.lbl_connect = Gtk.Label(label="Connect" if is_auth else "Sign in")
        self.lbl_connect.set_valign(Gtk.Align.CENTER)
        self.lbl_connect.set_halign(Gtk.Align.CENTER)

        connect_content.append(self.img_connect_icon)
        connect_content.append(self.lbl_connect)
        self.btn_connect.set_child(connect_content)
        self.banner_box.append(self.btn_connect)

        # Add banner_box as overlay on top of the world map
        self.hero_overlay.add_overlay(self.banner_box)
        self.hero_overlay.set_measure_overlay(self.banner_box, True)

        # disc_box alias for backward compatibility
        self.disc_box = self.banner_box

        return self.hero_overlay

    def _build_bottom_details_section(self) -> Gtk.Widget:
        """Calm, evenly-aligned security summary: one label style, no dividers."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.add_css_class("mullvad-details-card")
        card.add_css_class("mbvpn-details-card")
        card.set_halign(Gtk.Align.FILL)
        card.set_valign(Gtk.Align.FILL)

        # Section heading with neutral protocol metadata on the right
        h_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_head = Gtk.Label(label="SECURITY & PRIVACY")
        lbl_head.add_css_class("mullvad-details-header")
        lbl_head.add_css_class("mbvpn-details-header")
        lbl_head.set_hexpand(True)
        lbl_head.set_xalign(0)
        lbl_head.set_valign(Gtk.Align.CENTER)

        lbl_proto = Gtk.Label(label="WireGuard · 256-bit")
        lbl_proto.add_css_class("mbvpn-proto-badge")
        lbl_proto.set_valign(Gtk.Align.CENTER)
        h_box.append(lbl_head)
        h_box.append(lbl_proto)
        card.append(h_box)

        net_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        net_panel.add_css_class("mbvpn-network-panel")
        net_panel.set_halign(Gtk.Align.FILL)

        row_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=22)
        row_top.set_halign(Gtk.Align.FILL)

        # Left Column: time connected, value + caption, then the weekly chart
        col_time = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col_time.set_hexpand(True)
        col_time.set_valign(Gtk.Align.START)

        lbl_time_title = Gtk.Label(label="TIME CONNECTED")
        lbl_time_title.add_css_class("mbvpn-panel-label")
        lbl_time_title.set_xalign(0)
        lbl_time_title.set_tooltip_text("Tracked while Malwarebytes VPN is active")

        time_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        time_content.set_valign(Gtk.Align.END)

        self.lbl_protection_total = Gtk.Label(label="0h")
        self.lbl_protection_total.add_css_class("mbvpn-time-total")
        self.lbl_protection_total.set_xalign(0)

        self.lbl_protection_caption = Gtk.Label(label="this week")
        self.lbl_protection_caption.add_css_class("mbvpn-time-caption")
        self.lbl_protection_caption.set_xalign(0)
        self.lbl_protection_caption.set_valign(Gtk.Align.END)
        self.lbl_protection_caption.set_margin_bottom(1)

        time_content.append(self.lbl_protection_total)
        time_content.append(self.lbl_protection_caption)

        self.protection_chart = ProtectionChart()
        self.protection_chart.set_hexpand(True)
        self.protection_chart.set_valign(Gtk.Align.START)

        col_time.append(lbl_time_title)
        col_time.append(time_content)
        col_time.append(self.protection_chart)
        row_top.append(col_time)
        self._refresh_protection_chart()

        # Virtual IP fallback attribute (kept for status polling / tooltips)
        acct = self.backend.get_account_details()
        self.lbl_ip_val = Gtk.Label(label=acct.get("ipv4", "10.64.0.1") if self.is_connected else "Unprotected")

        # Right Column: kill switch, status + toggle, explanatory hint
        col_ks = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col_ks.set_hexpand(True)
        col_ks.set_valign(Gtk.Align.START)

        lbl_ks_title = Gtk.Label(label="KILL SWITCH")
        lbl_ks_title.add_css_class("mbvpn-panel-label")
        lbl_ks_title.set_xalign(0)

        ks_on = bool(self.settings.get("kill_switch", False))
        if ks_on:
            label_text = "Active" if self.is_connected else "Armed"
            sub_class = "active" if self.is_connected else "armed"
        else:
            label_text = "Disabled"
            sub_class = "disabled"

        ks_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ks_row.set_valign(Gtk.Align.CENTER)

        self.lbl_ks_status = Gtk.Label(label=label_text)
        self.lbl_ks_status.add_css_class("mbvpn-panel-sub")
        self.lbl_ks_status.add_css_class(sub_class)
        self.lbl_ks_status.set_xalign(0)
        self.lbl_ks_status.set_hexpand(True)

        # iOS/macOS toggle with 48x36px touch target
        switch_target = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        switch_target.add_css_class("mbvpn-switch-target")
        switch_target.set_size_request(48, 36)
        switch_target.set_valign(Gtk.Align.CENTER)
        switch_target.set_halign(Gtk.Align.END)

        self.switch_main_ks = Gtk.Switch()
        self.switch_main_ks.add_css_class("mbvpn-ios-switch")
        self.switch_main_ks.set_valign(Gtk.Align.CENTER)
        self.switch_main_ks.set_halign(Gtk.Align.END)
        self.switch_main_ks.set_active(ks_on)
        self.switch_main_ks.connect("notify::active", self._on_main_killswitch_toggled)
        switch_target.append(self.switch_main_ks)

        ks_row.append(self.lbl_ks_status)
        ks_row.append(switch_target)

        lbl_ks_hint = Gtk.Label(label="Blocks traffic if VPN drops")
        lbl_ks_hint.add_css_class("mbvpn-ks-hint")
        lbl_ks_hint.set_xalign(0)
        lbl_ks_hint.set_wrap(False)

        col_ks.append(lbl_ks_title)
        col_ks.append(ks_row)
        col_ks.append(lbl_ks_hint)

        row_top.append(col_ks)
        net_panel.append(row_top)

        # Single hairline before the traffic figures
        sep_h = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep_h.add_css_class("mbvpn-h-sep")
        net_panel.append(sep_h)

        # Bottom Row: session traffic
        traffic_strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        traffic_strip.add_css_class("mbvpn-traffic-strip")

        lbl_traffic_tag = Gtk.Label(label="SESSION TRAFFIC")
        lbl_traffic_tag.add_css_class("mbvpn-details-subtle")
        lbl_traffic_tag.set_hexpand(True)
        lbl_traffic_tag.set_xalign(0)
        lbl_traffic_tag.set_valign(Gtk.Align.CENTER)

        traffic_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        traffic_box.set_valign(Gtk.Align.CENTER)

        # Download readout (emerald arrow + clean metric)
        down_group = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        down_group.set_valign(Gtk.Align.CENTER)
        lbl_down_arrow = Gtk.Label(label="↓")
        lbl_down_arrow.add_css_class("mbvpn-traffic-down-arrow")
        lbl_down_arrow.set_valign(Gtk.Align.CENTER)
        self.lbl_down = Gtk.Label(label="0.0 MB")
        self.lbl_down.add_css_class("mullvad-details-val")
        self.lbl_down.add_css_class("mbvpn-details-val")
        self.lbl_down.add_css_class("mbvpn-traffic-val")
        self.lbl_down.set_valign(Gtk.Align.CENTER)
        down_group.append(lbl_down_arrow)
        down_group.append(self.lbl_down)

        # Upload readout (sky blue arrow + clean metric)
        up_group = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        up_group.set_valign(Gtk.Align.CENTER)
        lbl_up_arrow = Gtk.Label(label="↑")
        lbl_up_arrow.add_css_class("mbvpn-traffic-up-arrow")
        lbl_up_arrow.set_valign(Gtk.Align.CENTER)
        self.lbl_up = Gtk.Label(label="0.0 MB")
        self.lbl_up.add_css_class("mullvad-details-val")
        self.lbl_up.add_css_class("mbvpn-details-val")
        self.lbl_up.add_css_class("mbvpn-traffic-val")
        self.lbl_up.set_valign(Gtk.Align.CENTER)
        up_group.append(lbl_up_arrow)
        up_group.append(self.lbl_up)

        self.lbl_tunnel = Gtk.Label(label="Inactive")
        self.lbl_dns_status = Gtk.Label(label="Protected" if self.settings.get("dns_leak_shield", True) else "Off")

        traffic_box.append(down_group)
        traffic_box.append(up_group)

        traffic_strip.append(lbl_traffic_tag)
        traffic_strip.append(traffic_box)
        net_panel.append(traffic_strip)

        card.append(net_panel)
        return card

    def _build_footer_section(self) -> Gtk.Widget:
        """Subtle and refined creator credit anchored at the window footer."""
        footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        footer_box.add_css_class("mbvpn-credit-box")
        footer_box.add_css_class("mullvad-credit-box")
        footer_box.set_halign(Gtk.Align.CENTER)
        footer_box.set_margin_top(6)
        footer_box.set_margin_bottom(2)

        lbl_credit = Gtk.Label()
        lbl_credit.add_css_class("mbvpn-credit-label")
        lbl_credit.add_css_class("mullvad-credit-label")
        lbl_credit.set_markup('Made with <span foreground="#fb7185">♥</span> by <a href="https://x.com/drybyte">DryByte</a>')

        def on_link_activated(label, uri):
            try:
                Gio.AppInfo.launch_default_for_uri(uri, None)
                return True
            except Exception:
                try:
                    subprocess.Popen(["xdg-open", uri])
                    return True
                except Exception:
                    return False

        lbl_credit.connect("activate-link", on_link_activated)
        footer_box.append(lbl_credit)
        return footer_box

    def _build_location_selector_card(self) -> Gtk.Widget:
        """Malwarebytes Location Selection Card with Official Vector/WebP Flags"""
        btn = Gtk.Button()
        btn.add_css_class("mullvad-location-card")
        btn.add_css_class("mbvpn-location-card")
        btn.set_halign(Gtk.Align.FILL)
        btn.connect("clicked", lambda _: self._show_server_browser_modal())

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=13)

        # Flag badge container: squircle icon tile framing the circular flag
        flag_frame = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        flag_frame.add_css_class("mbvpn-flag-frame")
        flag_frame.set_valign(Gtk.Align.CENTER)
        flag_frame.set_halign(Gtk.Align.CENTER)

        self.img_flag = Gtk.Image()
        self.img_flag.set_pixel_size(30)
        self.img_flag.add_css_class("official-flag-icon")
        self.img_flag.set_valign(Gtk.Align.CENTER)
        self.img_flag.set_halign(Gtk.Align.CENTER)

        self.lbl_flag = Gtk.Label(label=self.selected_flag)
        self.lbl_flag.add_css_class("badge-flag")
        self.lbl_flag.set_valign(Gtk.Align.CENTER)
        self.lbl_flag.set_halign(Gtk.Align.CENTER)

        flag_frame.append(self.img_flag)
        flag_frame.append(self.lbl_flag)
        box.append(flag_frame)

        vtext = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vtext.set_hexpand(True)
        vtext.set_valign(Gtk.Align.CENTER)

        self.lbl_loc_name = Gtk.Label(label=self.selected_label)
        self.lbl_loc_name.add_css_class("mullvad-country")
        self.lbl_loc_name.add_css_class("mbvpn-country")
        self.lbl_loc_name.set_xalign(0)
        self.lbl_loc_name.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_loc_name.set_max_width_chars(24)

        self.lbl_loc_sub = Gtk.Label(label=self.selected_sub)
        self.lbl_loc_sub.set_use_markup(True)
        self.lbl_loc_sub.add_css_class("mullvad-city")
        self.lbl_loc_sub.add_css_class("mbvpn-city")
        self.lbl_loc_sub.set_xalign(0)
        self.lbl_loc_sub.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_loc_sub.set_max_width_chars(32)

        vtext.append(self.lbl_loc_name)
        vtext.append(self.lbl_loc_sub)
        box.append(vtext)

        img_arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
        img_arrow.set_pixel_size(14)
        img_arrow.set_valign(Gtk.Align.CENTER)
        img_arrow.add_css_class("mbvpn-loc-chevron")
        box.append(img_arrow)

        btn.set_child(box)
        self.btn_location = btn

        self._update_flag_icon()
        return btn

    def _get_solar_info(self, key: str):
        """Calculates real-world local solar time and diurnal phase from geographic coordinates."""
        coords = None
        try:
            if hasattr(self, "world_map") and hasattr(self.world_map, "_coords_db"):
                db = self.world_map._coords_db
                k = (key or "").lower().strip()
                candidates = [k]
                if "-" in k:
                    parts = k.split("-")
                    candidates.append("-".join(parts[:2]))  # e.g. de-fra
                    candidates.append(parts[0])             # e.g. de
                    if len(parts) >= 2:
                        candidates.append(parts[1])         # e.g. fra
                for cand in candidates:
                    if cand in db:
                        coords = db[cand]
                        break

            if not coords:
                return None, "night"

            lat, lon = coords
            now_utc = datetime.now(timezone.utc)
            offset_hours = float(lon) / 15.0
            local_seconds = (now_utc.hour * 3600 + now_utc.minute * 60 + now_utc.second + offset_hours * 3600) % 86400
            local_hour = int(local_seconds // 3600)
            local_minute = int((local_seconds % 3600) // 60)
            period = "AM" if local_hour < 12 else "PM"
            display_hour = local_hour % 12 or 12
            time_str = f"{display_hour}:{local_minute:02d} {period}"

            if 6 <= local_hour < 8 or 17 <= local_hour < 19:
                phase = "twilight"
            elif 8 <= local_hour < 17:
                phase = "day"
            else:
                phase = "night"

            return time_str, phase
        except Exception:
            return None, "night"

    def _update_location_diurnal(self, server_override: str = None):
        """Applies dynamic diurnal atmospheric surface and local solar time to the location card."""
        if not hasattr(self, "btn_location") or not self.btn_location:
            return

        target = server_override
        if not target:
            if getattr(self, "is_connected", False) and hasattr(self, "current_status") and self.current_status and self.current_status.server:
                target = self.current_status.server
            else:
                target = getattr(self, "selected_target", "sg")

        time_info = self._get_solar_info(target)
        if time_info and time_info[0]:
            time_str, phase = time_info[0], time_info[1]
        else:
            time_str, phase = None, "night"

        self.btn_location.remove_css_class("mbvpn-loc-day")
        self.btn_location.remove_css_class("mbvpn-loc-twilight")
        self.btn_location.remove_css_class("mbvpn-loc-night")

        if hasattr(self, "lbl_loc_sub"):
            if getattr(self, "is_connected", False) and hasattr(self, "current_status") and self.current_status and self.current_status.server:
                node = self.current_status.server
            elif hasattr(self, "selected_sub") and self.selected_sub:
                node = self._clean_sub_text(self.selected_sub)
            else:
                node = "Optimal Server"

            esc_node = GLib.markup_escape_text(str(node))
            if time_str:
                esc_time = GLib.markup_escape_text(str(time_str))
                markup = f"<span color=\"#94a3b8\">{esc_node}</span> <span color=\"#475569\">·</span> <span color=\"#cbd5e1\">{esc_time}</span>"
            else:
                markup = f"<span color=\"#94a3b8\">{esc_node}</span>"
            self.lbl_loc_sub.set_markup(markup)

    def _update_flag_icon(self, cc_override: str = None):
        """Displays official WebP flag image if present, otherwise falls back to text flag."""
        if cc_override:
            cc = cc_override.lower()
        elif getattr(self, "is_connected", False) and hasattr(self, "current_status") and self.current_status and self.current_status.server:
            cc = (self.current_status.server.split("-")[0]).lower()
        else:
            target = self.selected_target or "sg"
            cc = (target[:2]).lower()

        flag_path = str(ASSETS_DIR / "flags" / f"flag_{cc}.webp")
        if hasattr(self, "img_flag") and self.img_flag:
            if os.path.exists(flag_path):
                try:
                    tex = Gdk.Texture.new_from_filename(flag_path)
                    self.img_flag.set_from_paintable(tex)
                    self.img_flag.set_pixel_size(30)
                    self.img_flag.set_visible(True)
                    if hasattr(self, "lbl_flag") and self.lbl_flag:
                        self.lbl_flag.set_visible(False)
                    self._update_location_diurnal(cc_override)
                    return
                except Exception as e:
                    pass
            self.img_flag.set_visible(False)
            if hasattr(self, "lbl_flag") and self.lbl_flag:
                if len(cc) == 2:
                    emoji = chr(127397 + ord(cc[0].upper())) + chr(127397 + ord(cc[1].upper()))
                    self.lbl_flag.set_label(emoji)
                self.lbl_flag.set_visible(True)

        self._update_location_diurnal(cc_override)

    def _build_telemetry_section(self) -> Gtk.Widget:
        return self.telemetry_box

    def _build_security_preferences_section(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.set_title("Security and Tunnel Preferences")

        # 1. Kill Switch
        self.switch_killswitch = Adw.SwitchRow()
        self.switch_killswitch.set_title("Internet Kill Switch")
        self.switch_killswitch.set_subtitle("Block all network traffic if the VPN connection drops unexpectedly")
        self.switch_killswitch.add_prefix(Gtk.Image.new_from_icon_name("network-vpn-symbolic"))
        self.switch_killswitch.set_active(self.settings.get("kill_switch", False))
        self.switch_killswitch.connect("notify::active", self._on_killswitch_toggled)
        group.add(self.switch_killswitch)

        self.switch_hard_killswitch = Adw.SwitchRow()
        self.switch_hard_killswitch.set_active(self.settings.get("hard_kill_switch", False))
        self.switch_hard_killswitch.connect("notify::active", self._on_hard_killswitch_toggled)

        # 2. DNS Leak Shield
        self.switch_dns = Adw.SwitchRow()
        self.switch_dns.set_title("DNS Leak Shield")
        self.switch_dns.set_subtitle("Force all DNS queries exclusively through WireGuard resolver")
        self.switch_dns.add_prefix(Gtk.Image.new_from_icon_name("channel-secure-symbolic"))
        self.switch_dns.set_active(self.settings.get("dns_leak_shield", True))
        self.switch_dns.connect("notify::active", self._on_dns_shield_toggled)
        group.add(self.switch_dns)

        # 3. Auto-Reconnect
        self.switch_autoreconnect = Adw.SwitchRow()
        self.switch_autoreconnect.set_title("Auto-Reconnect")
        self.switch_autoreconnect.set_subtitle("Automatically re-establish connection if the tunnel drops")
        self.switch_autoreconnect.add_prefix(Gtk.Image.new_from_icon_name("system-software-update-symbolic"))
        self.switch_autoreconnect.set_active(self.settings.get("auto_reconnect", True))
        self.switch_autoreconnect.connect("notify::active", self._on_autoreconnect_toggled)
        group.add(self.switch_autoreconnect)

        # 4. Auto-Connect on Startup
        self.switch_autoconnect = Adw.SwitchRow()
        self.switch_autoconnect.set_title("Auto-Connect on Startup")
        self.switch_autoconnect.set_subtitle("Automatically connect when the application starts")
        self.switch_autoconnect.add_prefix(Gtk.Image.new_from_icon_name("starred-symbolic"))
        self.switch_autoconnect.set_active(self.settings.get("auto_connect", False))
        self.switch_autoconnect.connect("notify::active", self._on_autoconnect_toggled)
        group.add(self.switch_autoconnect)

        # 5. Minimize to System Tray
        self.switch_tray = Adw.SwitchRow()
        self.switch_tray.set_title("Minimize to System Tray")
        self.switch_tray.set_subtitle("Keep VPN active in Omarchy status bar when closing window")
        self.switch_tray.add_prefix(Gtk.Image.new_from_icon_name("view-paged-symbolic"))
        self.switch_tray.set_active(self.settings.get("minimize_to_tray", True))
        self.switch_tray.connect("notify::active", self._on_tray_toggled)
        group.add(self.switch_tray)

        # 6. Active Relay Node
        self.row_relay = Adw.ActionRow()
        self.row_relay.set_title("Active WireGuard Relay")
        self.row_relay.set_subtitle("None")
        self.row_relay.add_prefix(Gtk.Image.new_from_icon_name("network-wired-symbolic"))
        group.add(self.row_relay)

        # 7. Encryption Protocol
        self.row_proto = Adw.ActionRow()
        self.row_proto.set_title("Tunnel Encryption")
        self.row_proto.set_subtitle("WireGuard • ChaCha20-Poly1305 • 256-bit")
        self.row_proto.add_prefix(Gtk.Image.new_from_icon_name("security-high-symbolic"))
        group.add(self.row_proto)

        self.security_preferences_group = group
        return group

    def _show_settings_dialog(self):
        """Settings, Kill Switch, DNS Shield, and Tunnel Configuration Modal"""
        dialog = Adw.Window(transient_for=self, modal=True)
        dialog.add_css_class("mullvad-window")
        dialog.set_title("Settings")
        dialog.set_default_size(380, 560)
        dialog.set_size_request(360, 500)
        dialog.set_resizable(False)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        dialog.set_content(main_box)

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Settings"))

        btn_ref = Gtk.Button(icon_name="view-refresh-symbolic")
        btn_ref.set_tooltip_text("Refresh Network Status")
        btn_ref.connect("clicked", lambda _: self.refresh_async())
        header.pack_start(btn_ref)

        main_box.append(header)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        main_box.append(scroller)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        content.set_margin_top(12)
        content.set_margin_bottom(20)
        content.set_margin_start(14)
        content.set_margin_end(14)
        scroller.set_child(content)

        # Security & Preferences group
        group = Adw.PreferencesGroup()
        group.set_title("Security and Privacy")

        sw_kill = Adw.SwitchRow()
        sw_kill.set_title("Internet Kill Switch")
        sw_kill.set_subtitle("Block all network traffic if the VPN connection drops unexpectedly")
        sw_kill.add_prefix(Gtk.Image.new_from_icon_name("network-vpn-symbolic"))
        sw_kill.set_active(self.settings.get("kill_switch", False))
        def on_ks(row, _):
            self.switch_killswitch.set_active(row.get_active())
        sw_kill.connect("notify::active", on_ks)
        group.add(sw_kill)

        sw_hard = Adw.SwitchRow()
        sw_hard.set_title("Hard Kill Switch")
        sw_hard.set_subtitle("Block all internet unless the VPN is connected. Only the VPN server can be reached to reconnect.")
        sw_hard.add_prefix(Gtk.Image.new_from_icon_name("channel-secure-symbolic"))
        sw_hard.set_active(self.settings.get("hard_kill_switch", False))
        self.settings_hard_row = sw_hard
        sw_hard.connect("notify::active", lambda row, _: self.switch_hard_killswitch.set_active(row.get_active()))
        group.add(sw_hard)

        sw_dns = Adw.SwitchRow()
        sw_dns.set_title("DNS Leak Shield")
        sw_dns.set_subtitle("Force all DNS queries exclusively through WireGuard resolver")
        sw_dns.add_prefix(Gtk.Image.new_from_icon_name("channel-secure-symbolic"))
        sw_dns.set_active(self.settings.get("dns_leak_shield", True))
        def on_ds(row, _):
            self.switch_dns.set_active(row.get_active())
        sw_dns.connect("notify::active", on_ds)
        group.add(sw_dns)

        sw_rec = Adw.SwitchRow()
        sw_rec.set_title("Auto-Reconnect")
        sw_rec.set_subtitle("Automatically re-establish connection if the tunnel drops")
        sw_rec.add_prefix(Gtk.Image.new_from_icon_name("system-software-update-symbolic"))
        sw_rec.set_active(self.settings.get("auto_reconnect", True))
        def on_ar(row, _):
            self.switch_autoreconnect.set_active(row.get_active())
        sw_rec.connect("notify::active", on_ar)
        group.add(sw_rec)

        sw_con = Adw.SwitchRow()
        sw_con.set_title("Auto-Connect on Startup")
        sw_con.set_subtitle("Automatically connect when the application starts")
        sw_con.add_prefix(Gtk.Image.new_from_icon_name("starred-symbolic"))
        sw_con.set_active(self.settings.get("auto_connect", False))
        def on_ac(row, _):
            self.switch_autoconnect.set_active(row.get_active())
        sw_con.connect("notify::active", on_ac)
        group.add(sw_con)

        sw_tray = Adw.SwitchRow()
        sw_tray.set_title("Minimize to System Tray")
        sw_tray.set_subtitle("Keep VPN active in Omarchy status bar when closing window")
        sw_tray.add_prefix(Gtk.Image.new_from_icon_name("view-paged-symbolic"))
        sw_tray.set_active(self.settings.get("minimize_to_tray", True))
        def on_tr(row, _):
            self.switch_tray.set_active(row.get_active())
        sw_tray.connect("notify::active", on_tr)
        group.add(sw_tray)

        content.append(group)

        # Hardware Privacy & MAC Address Changer
        group_mac = Adw.PreferencesGroup()
        group_mac.set_title("Hardware Privacy &amp; MAC Address Changer")
        group_mac.set_description("Prevent physical hardware tracking across local Wi-Fi networks")

        mac_info = self.backend.get_mac_info()

        # Row 1: Current MAC Address
        row_cur_mac = Adw.ActionRow()
        row_cur_mac.set_title("Current Active MAC")
        row_cur_mac.set_subtitle(f"{mac_info['current_mac']} ({mac_info['interface']})")
        row_cur_mac.add_prefix(Gtk.Image.new_from_icon_name("network-wireless-symbolic"))

        badge_mac = Gtk.Label()
        if mac_info["is_spoofed"]:
            badge_mac.set_label("Randomized")
            badge_mac.add_css_class("mullvad-details-badge")
        else:
            badge_mac.set_label("Hardware Default")
            badge_mac.add_css_class("mullvad-details-badge-off")
        badge_mac.set_valign(Gtk.Align.CENTER)
        row_cur_mac.add_suffix(badge_mac)
        group_mac.add(row_cur_mac)

        # Wi-Fi MAC Randomization Switch
        sw_mac_rand = Adw.SwitchRow()
        sw_mac_rand.set_title("Wi-Fi MAC Randomization")
        sw_mac_rand.set_subtitle("Automatically assign a randomized MAC address on each Wi-Fi connection")
        sw_mac_rand.add_prefix(Gtk.Image.new_from_icon_name("security-high-symbolic"))
        sw_mac_rand.set_active(self.settings.get("mac_randomization", True) or mac_info.get("cloned_mode") == "random")
        def on_mac_rand(row, _):
            val = row.get_active()
            self.settings["mac_randomization"] = val
            self._save_settings()
            success, msg = self.backend.set_mac_randomization(val)
            if success:
                updated_info = self.backend.get_mac_info()
                if val:
                    badge_mac.set_label("Randomized")
                    badge_mac.remove_css_class("mullvad-details-badge-off")
                    badge_mac.add_css_class("mullvad-details-badge")
                else:
                    badge_mac.set_label("Hardware Default")
                    badge_mac.remove_css_class("mullvad-details-badge")
                    badge_mac.add_css_class("mullvad-details-badge-off")
            else:
                self._show_toast(f"MAC setting error: {msg}")
        sw_mac_rand.connect("notify::active", on_mac_rand)
        group_mac.add(sw_mac_rand)

        # Row 4: Generate New Random MAC Action
        row_gen_mac = Adw.ActionRow()
        row_gen_mac.set_title("Generate New Random MAC")
        row_gen_mac.set_subtitle("Assign a fresh locally-administered unicast MAC address")
        row_gen_mac.add_prefix(Gtk.Image.new_from_icon_name("system-software-update-symbolic"))
        btn_gen_mac = Gtk.Button(label="Randomize MAC")
        btn_gen_mac.set_valign(Gtk.Align.CENTER)
        btn_gen_mac.add_css_class("suggested-action")
        def on_gen_mac_clicked(_):
            new_mac = self.backend.generate_random_mac()
            success, msg = self.backend.set_custom_mac(new_mac)
            if success:
                row_cur_mac.set_subtitle(f"{new_mac} ({mac_info['interface']})")
                badge_mac.set_label("Randomized")
                badge_mac.remove_css_class("mullvad-details-badge-off")
                badge_mac.add_css_class("mullvad-details-badge")
            else:
                self._show_toast(f"Failed to assign MAC: {msg}")
        btn_gen_mac.connect("clicked", on_gen_mac_clicked)
        row_gen_mac.add_suffix(btn_gen_mac)
        group_mac.add(row_gen_mac)

        # Row 5: Restore Factory Hardware MAC Action
        row_rest_mac = Adw.ActionRow()
        row_rest_mac.set_title("Restore Hardware MAC")
        row_rest_mac.set_subtitle("Revert network interface to original factory hardware MAC")
        row_rest_mac.add_prefix(Gtk.Image.new_from_icon_name("edit-undo-symbolic"))
        btn_rest_mac = Gtk.Button(label="Restore Factory")
        btn_rest_mac.set_valign(Gtk.Align.CENTER)
        def on_rest_mac_clicked(_):
            success, msg = self.backend.restore_hardware_mac()
            if success:
                row_cur_mac.set_subtitle(f"{mac_info['permanent_mac']} ({mac_info['interface']})")
                badge_mac.set_label("Hardware Default")
                badge_mac.remove_css_class("mullvad-details-badge")
                badge_mac.add_css_class("mullvad-details-badge-off")
            else:
                self._show_toast(f"Failed to restore MAC: {msg}")
        btn_rest_mac.connect("clicked", on_rest_mac_clicked)
        row_rest_mac.add_suffix(btn_rest_mac)
        group_mac.add(row_rest_mac)

        content.append(group_mac)

        # WireGuard Tunnel Group
        group_proto = Adw.PreferencesGroup()
        group_proto.set_title("WireGuard Architecture")

        row_relay = Adw.ActionRow()
        row_relay.set_title("Active WireGuard Relay")
        row_relay.set_subtitle(self.row_relay.get_subtitle())
        row_relay.add_prefix(Gtk.Image.new_from_icon_name("network-wired-symbolic"))
        group_proto.add(row_relay)

        row_proto = Adw.ActionRow()
        row_proto.set_title("Tunnel Encryption")
        row_proto.set_subtitle("WireGuard • ChaCha20-Poly1305 • 256-bit")
        row_proto.add_prefix(Gtk.Image.new_from_icon_name("channel-secure-symbolic"))
        group_proto.add(row_proto)

        content.append(group_proto)

        # System Actions Group
        group_act = Adw.PreferencesGroup()
        group_act.set_title("System Actions")

        btn_cap = Gtk.Button(label="Check and Fix WireGuard Permissions")
        btn_cap.add_css_class("flat")
        btn_cap.connect("clicked", lambda _: self._fix_capabilities())
        group_act.add(btn_cap)

        btn_q = Gtk.Button(label="Quit MalwarebytesVPN")
        btn_q.add_css_class("destructive-action")
        btn_q.set_margin_top(8)
        btn_q.connect("clicked", lambda _: self._quit_application())
        group_act.add(btn_q)

        content.append(group_act)

        # About Group with Creator Attribution
        group_about = Adw.PreferencesGroup()
        group_about.set_title("About")
        row_about = Adw.ActionRow()
        row_about.set_title("Malwarebytes Privacy VPN Client")
        row_about.add_prefix(Gtk.Image.new_from_icon_name("help-about-symbolic"))

        def open_drybyte_twitter(*_):
            uri = "https://x.com/drybyte"
            try:
                Gio.AppInfo.launch_default_for_uri(uri, None)
            except Exception:
                try:
                    subprocess.Popen(["xdg-open", uri])
                except Exception:
                    pass
            return True

        row_about.set_activatable(True)
        row_about.connect("activated", open_drybyte_twitter)

        btn_tw = Gtk.Button.new_from_icon_name("adw-external-link-symbolic")
        btn_tw.add_css_class("flat")
        btn_tw.set_valign(Gtk.Align.CENTER)
        btn_tw.set_tooltip_text("Open @DryByte on X (Twitter)")
        btn_tw.connect("clicked", open_drybyte_twitter)
        row_about.add_suffix(btn_tw)

        # Direct click controller on row
        gesture = Gtk.GestureClick()
        gesture.connect("released", lambda *_: open_drybyte_twitter())
        row_about.add_controller(gesture)

        # Psychologically appealing breathing animation: 3.6s rich aurora spectrum
        # Colors: Electric Cyan (#22d3ee) -> Neon Indigo (#818cf8) -> Luminous Orchid (#e879f9) -> Vivid Sky (#38bdf8)
        aurora_stops = [
            (34, 211, 238),   # #22d3ee - Electric Cyan
            (129, 140, 248),  # #818cf8 - Neon Indigo
            (232, 121, 249),  # #e879f9 - Luminous Orchid / Pink
            (56, 189, 248),   # #38bdf8 - Vivid Sky Blue
        ]
        start_time = time.time()
        def _on_breath_tick():
            if not dialog.get_visible():
                return False
            t = time.time() - start_time
            cycle = 3.6
            p = ((t % cycle) / cycle) * len(aurora_stops)
            idx = int(p)
            f = p - idx
            # Smoothstep easing
            f = f * f * (3 - 2 * f)

            c1 = aurora_stops[idx % len(aurora_stops)]
            c2 = aurora_stops[(idx + 1) % len(aurora_stops)]

            r = int(c1[0] + (c2[0] - c1[0]) * f)
            g = int(c1[1] + (c2[1] - c1[1]) * f)
            b = int(c1[2] + (c2[2] - c1[2]) * f)
            color = f"#{r:02x}{g:02x}{b:02x}"

            # Subtle organic heart pulse (#fb7185 to #fda4af)
            heart_phase = (t % 1.8) / 1.8 * 2 * math.pi
            hf = 0.5 - 0.5 * math.cos(heart_phase)
            hr = int(251 + (253 - 251) * hf)
            hg = int(113 + (164 - 113) * hf)
            hb = int(133 + (175 - 133) * hf)
            hcolor = f"#{hr:02x}{hg:02x}{hb:02x}"

            # Clean bold text without browser link underline
            markup = f'Engineered with <span foreground="{hcolor}">♥</span> by <span foreground="{color}" font_weight="bold">DryByte</span>'
            row_about.set_subtitle(markup)
            return True

        # Initial subtitle state
        _on_breath_tick()
        breath_timer_id = GLib.timeout_add(33, _on_breath_tick)

        def _on_dialog_closed(w):
            try:
                GLib.source_remove(breath_timer_id)
            except Exception:
                pass
            return False

        dialog.connect("close-request", _on_dialog_closed)

        group_about.add(row_about)
        content.append(group_about)

        dialog.present()
        return dialog

    def _on_tray_toggled(self, row, _):
        active = row.get_active()
        self.settings["minimize_to_tray"] = active
        self._save_settings()

    def _on_killswitch_toggled(self, row, _):
        active = row.get_active()
        self.settings["kill_switch"] = active
        if not active:
            self.settings["hard_kill_switch"] = False
            if hasattr(self, "switch_hard_killswitch"):
                self.switch_hard_killswitch.set_active(False)
            if hasattr(self, "settings_hard_row"):
                self.settings_hard_row.set_active(False)
        self._save_settings()

        if hasattr(self, "switch_main_ks") and not getattr(self, "_ks_syncing", False):
            self._ks_syncing = True
            try:
                if self.switch_main_ks.get_active() != active:
                    self.switch_main_ks.set_active(active)
            finally:
                self._ks_syncing = False

        if hasattr(self, "lbl_ks_status"):
            if active:
                self.lbl_ks_status.set_label("Active" if getattr(self, "is_connected", False) else "Armed")
                self.lbl_ks_status.remove_css_class("disabled")
                self.lbl_ks_status.add_css_class("active" if getattr(self, "is_connected", False) else "armed")
            else:
                self.lbl_ks_status.set_label("Disabled")
                self.lbl_ks_status.remove_css_class("active")
                self.lbl_ks_status.remove_css_class("armed")
                self.lbl_ks_status.add_css_class("disabled")

        if active:
            if not self.backend.has_firewall_capabilities():
                self._fix_capabilities()
                return

            if getattr(self, "is_connected", False):
                def worker_enable():
                    success, msg = self.backend.enable_killswitch(
                        bypass_apps=self.settings.get("bypass_apps", []),
                        bypass_antigravity=self.settings.get("bypass_antigravity", True),
                        hard=self.settings.get("hard_kill_switch", False),
                    )
                    def finish():
                        if not success:
                            self._show_toast(f"Kill Switch error: {msg}")
                        self.refresh_async()
                        return False
                    GLib.idle_add(finish)

                threading.Thread(target=worker_enable, daemon=True).start()
            else:
                self.refresh_async()
        else:
            def worker_disable():
                success, msg = self.backend.disable_killswitch()
                def finish():
                    if not success:
                        self._show_toast(f"Kill Switch: {msg}")
                    self.refresh_async()
                    return False
                GLib.idle_add(finish)

            threading.Thread(target=worker_disable, daemon=True).start()

    def _on_main_killswitch_toggled(self, switch, _):
        if getattr(self, "_ks_syncing", False):
            return
        active = switch.get_active()
        self._ks_syncing = True
        try:
            if hasattr(self, "switch_killswitch") and self.switch_killswitch.get_active() != active:
                self.switch_killswitch.set_active(active)
            else:
                self.settings["kill_switch"] = active
                self._save_settings()
                if hasattr(self, "lbl_ks_status"):
                    if active:
                        self.lbl_ks_status.set_label("Active" if getattr(self, "is_connected", False) else "Armed")
                        self.lbl_ks_status.remove_css_class("disabled")
                        self.lbl_ks_status.add_css_class("active" if getattr(self, "is_connected", False) else "armed")
                    else:
                        self.lbl_ks_status.set_label("Disabled")
                        self.lbl_ks_status.remove_css_class("active")
                        self.lbl_ks_status.remove_css_class("armed")
                        self.lbl_ks_status.add_css_class("disabled")
                if active:
                    if not self.backend.has_firewall_capabilities():
                        self._fix_capabilities()
                        return
                    if getattr(self, "is_connected", False):
                        def worker_enable():
                            success, msg = self.backend.enable_killswitch(
                                bypass_apps=self.settings.get("bypass_apps", []),
                                bypass_antigravity=self.settings.get("bypass_antigravity", True),
                                hard=self.settings.get("hard_kill_switch", False),
                            )
                            def finish():
                                if not success:
                                    self._show_toast(f"Kill Switch error: {msg}")
                                self.refresh_async()
                                return False
                            GLib.idle_add(finish)
                        threading.Thread(target=worker_enable, daemon=True).start()
                    else:
                        self.refresh_async()
                else:
                    def worker_disable():
                        success, msg = self.backend.disable_killswitch()
                        def finish():
                            if not success:
                                self._show_toast(f"Kill Switch: {msg}")
                            self.refresh_async()
                            return False
                        GLib.idle_add(finish)
                    threading.Thread(target=worker_disable, daemon=True).start()
        finally:
            self._ks_syncing = False

    def _on_hard_killswitch_toggled(self, row, _):
        if getattr(self, "_ks_syncing", False):
            return
        active = row.get_active()
        if active and not self.backend.supports_hard_killswitch():
            self._ks_syncing = True
            row.set_active(False)
            self._ks_syncing = False
            self._show_toast("Update firewall helper by running setup.sh")
            return
        if active and not self.backend.has_firewall_capabilities():
            self._ks_syncing = True
            row.set_active(False)
            self._ks_syncing = False
            self._show_toast("Hard Kill Switch needs network capabilities. Run setup first.")
            return

        self.settings["hard_kill_switch"] = active
        self.settings["kill_switch"] = True if active else self.settings.get("kill_switch", False)
        self._save_settings()
        if active:
            self._ks_syncing = True
            try:
                if hasattr(self, "switch_killswitch"):
                    self.switch_killswitch.set_active(True)
                if hasattr(self, "switch_main_ks"):
                    self.switch_main_ks.set_active(True)
            finally:
                self._ks_syncing = False

        def worker():
            if active:
                # Only apply firewall rules if VPN is currently connected.
                # If disconnected, backend.enable_killswitch now returns armed state safely.
                status = self.backend.get_status()
                success, message = self.backend.enable_killswitch(
                    endpoint_ip=None,
                    bypass_apps=self.settings.get("bypass_apps", []),
                    bypass_antigravity=self.settings.get("bypass_antigravity", True),
                    hard=True,
                    tunnel_interface=self.backend.get_active_vpn_interface() if status.connected else None,
                )
            elif getattr(self, "is_connected", False) and self.settings.get("kill_switch"):
                success, message = self.backend.enable_killswitch(
                    bypass_apps=self.settings.get("bypass_apps", []),
                    bypass_antigravity=self.settings.get("bypass_antigravity", True),
                )
            else:
                success, message = self.backend.disable_killswitch()

            def finish():
                if not success and active:
                    self.settings["hard_kill_switch"] = False
                    self.settings["kill_switch"] = False
                    self._save_settings()
                    self._ks_syncing = True
                    row.set_active(False)
                    if hasattr(self, "switch_killswitch"):
                        self.switch_killswitch.set_active(False)
                    if hasattr(self, "switch_main_ks"):
                        self.switch_main_ks.set_active(False)
                    if hasattr(self, "settings_hard_row"):
                        self.settings_hard_row.set_active(False)
                    self._ks_syncing = False
                    self.backend.disable_killswitch()
                if not success:
                    self._show_toast(f"Kill Switch error: {message}")
                self.refresh_async()
                return False
            GLib.idle_add(finish)

        threading.Thread(target=worker, daemon=True).start()

    def _on_dns_shield_toggled(self, row, _):
        active = row.get_active()
        self.settings["dns_leak_shield"] = active
        self._save_settings()
        if hasattr(self, "lbl_dns_status"):
            self.lbl_dns_status.set_label("Protected" if active else "Off")
        if active and getattr(self, "is_connected", False):
            self.backend.enable_dns_protection()
        elif not active:
            self.backend.disable_dns_protection()

    def _on_autoreconnect_toggled(self, row, _):
        active = row.get_active()
        self.settings["auto_reconnect"] = active
        self._save_settings()

    def _on_autoconnect_toggled(self, row, _):
        active = row.get_active()
        self.settings["auto_connect"] = active
        self._save_settings()

    def _show_toast(self, message: str):
        toast = Adw.Toast.new(message)
        toast.set_timeout(2)
        self.toast_overlay.add_toast(toast)

    def _set_status_message(self, text: str, dot_color: str = None):
        """Render the status line, clamped so a long progress message can never widen the fixed-size window."""
        if not hasattr(self, "lbl_status_desc"):
            return
        if len(text) > 44:
            text = text[:41].rstrip() + "..."
        if dot_color:
            self.lbl_status_desc.set_markup(
                "<span foreground='%s'>\u25cf</span> %s" % (dot_color, GLib.markup_escape_text(text))
            )
        else:
            self.lbl_status_desc.set_label(text)
        # Progress detail lives in the tooltip, never in the pill
        self.lbl_status_desc.set_tooltip_text(None)

    def _set_busy(self, busy: bool, message: str = "", title: str = "", mode: str = "connecting"):
        already_busy = getattr(self, "is_busy", False)
        self.is_busy = busy
        self._busy_mode = mode
        if busy:
            if not already_busy:
                self._busy_since = time.time()
            # Only touch styling/animation on the first call of a transition so progress
            # updates cannot re-trigger style invalidation or restart the shield animation.
            if not already_busy:
                if hasattr(self, "cyber_shield"):
                    self.cyber_shield.start_animation(mode)
                if hasattr(self, "world_map"):
                    if mode == "connecting" and hasattr(self, "selected_target"):
                        self.world_map.set_target(server=self.selected_target)
                    self.world_map.set_state("connecting" if mode == "connecting" else "unprotected")
                self.btn_refresh.set_sensitive(False)
                self.banner_box.remove_css_class("mullvad-banner-unsecured")
                self.banner_box.remove_css_class("mullvad-banner-secured")
                self.banner_box.remove_css_class("mbvpn-hero-unsecured")
                self.banner_box.remove_css_class("mbvpn-hero-secured")
                self.banner_box.add_css_class("mullvad-banner-connecting")
                self.banner_box.add_css_class("mbvpn-hero-connecting")
                self._sync_connect_button()
            dot_color = "#38bdf8" if mode == "connecting" else "#fbbf24"
            # Compact pill: the verbose step stays in the tooltip so the chip never stretches
            if getattr(self, "_cancel_connect_requested", False) and mode == "connecting":
                pill = "Cancelling\u2026"
            else:
                pill = "Connecting\u2026" if mode == "connecting" else "Disconnecting\u2026"
            self._set_status_message(pill, dot_color=dot_color)
            self.lbl_status_desc.set_tooltip_text(message or pill)
            self._repaint_status()
        else:
            self.banner_box.remove_css_class("mbvpn-hero-connecting")
            self.banner_box.remove_css_class("mullvad-banner-connecting")
            self.btn_refresh.set_sensitive(True)
            if hasattr(self, "lbl_status_desc"):
                self.lbl_status_desc.set_tooltip_text(None)
            if hasattr(self, "cyber_shield"):
                self.cyber_shield.set_mode("protected" if self.is_connected else "unprotected")
            if hasattr(self, "world_map"):
                self.world_map.set_state("protected" if self.is_connected else "unprotected")
            self._sync_connect_button()
            self._repaint_status()

    def _sync_connect_button(self, logged_in: bool = None):
        """Keep the labelled connect control aligned with the current tunnel state."""
        if not hasattr(self, "btn_connect"):
            return
        if logged_in is None:
            logged_in = self.backend.is_logged_in()

        busy = getattr(self, "is_busy", False)
        connecting = getattr(self, "_busy_mode", "connecting") == "connecting"
        cancelling = getattr(self, "_cancel_connect_requested", False)

        if busy:
            connected = self.is_connected
            locked = False
            if connecting and cancelling:
                label = "Cancelling\u2026"
                icon = "process-stop-symbolic"
            elif connecting:
                label = "Cancel"
                icon = "process-stop-symbolic"
            else:
                label = "Disconnecting\u2026"
                icon = "system-shutdown-symbolic"
        elif self.is_connected:
            label = "Disconnect"
            icon = "system-shutdown-symbolic"
            connected = True
            locked = False
        elif logged_in:
            label = "Connect"
            icon = "system-shutdown-symbolic"
            connected = False
            locked = False
        else:
            label = "Sign in"
            icon = "avatar-default-symbolic"
            connected = False
            locked = True

        self.lbl_connect.set_label(label)
        self.img_connect_icon.set_from_icon_name(icon)
        self.img_connect_icon.set_visible(connected)
        # No tooltip on this control: the label already says Connect / Cancel / Disconnect,
        # and a hover card under the button reads as a duplicate, detached control.
        self.btn_connect.set_tooltip_text(None)
        # Cancel stays clickable while connecting; every other transition locks the control
        self.btn_connect.set_sensitive(not busy or (connecting and not cancelling))
        self.btn_connect.remove_css_class("accent")
        self.btn_connect.remove_css_class("connected")
        self.btn_connect.remove_css_class("locked")
        self.btn_connect.remove_css_class("idle")
        if busy:
            self.btn_connect.add_css_class("accent" if connecting else ("connected" if connected else "accent"))
        elif locked:
            self.btn_connect.add_css_class("locked")
        elif connected:
            self.btn_connect.add_css_class("connected")
        else:
            self.btn_connect.add_css_class("accent")
            self.btn_connect.add_css_class("idle")

    def _repaint_status(self):
        """Repaint the whole status block."""
        if hasattr(self, "banner_box"):
            self.banner_box.queue_draw()
        if hasattr(self, "status_vbox"):
            self.status_vbox.queue_draw()
        if hasattr(self, "lbl_status_desc"):
            self.lbl_status_desc.queue_draw()
        if hasattr(self, "btn_connect"):
            self.btn_connect.queue_draw()
        self.queue_draw()

    def _start_refresh_loop(self):
        def tick():
            if not self.is_busy:
                self.refresh_async(silent=True)
            return True

        GLib.timeout_add_seconds(5, tick)

    def refresh_async(self, silent: bool = False):
        def worker():
            status = self.backend.get_status()
            has_cap, _ = self.backend.check_capabilities()
            logged_in = self.backend.is_logged_in()
            GLib.idle_add(self._update_ui_state, status, has_cap, logged_in)

        threading.Thread(target=worker, daemon=True).start()

    def _protection_week_start(self):
        today = date.today()
        return today - timedelta(days=(today.weekday() + 1) % 7)

    def _refresh_protection_chart(self):
        week_start = self._protection_week_start()
        daily = self.settings.get("protection_daily", {})
        values = []
        for offset in range(7):
            day_key = (week_start + timedelta(days=offset)).isoformat()
            try:
                values.append(max(0.0, float(daily.get(day_key, 0))))
            except (TypeError, ValueError):
                values.append(0.0)

        total_seconds = sum(values)
        if 0 < total_seconds < 3600:
            total_label = f"{max(1, int(total_seconds // 60))}m"
        else:
            total_label = f"{int(total_seconds // 3600)}h"
        if hasattr(self, "lbl_protection_total"):
            self.lbl_protection_total.set_label(total_label)
        if hasattr(self, "protection_chart"):
            self.protection_chart.set_daily_seconds(values)

    def _record_protection_time(self):
        now = time.time()
        previous = self._protection_last_sample
        self._protection_last_sample = now
        if previous is None or not self.is_connected:
            return

        elapsed = min(max(now - previous, 0.0), 10.0)
        previous_day = datetime.fromtimestamp(previous).date()
        week_start = self._protection_week_start()
        if elapsed <= 0 or previous_day < week_start:
            return

        day_key = previous_day.isoformat()
        daily = self.settings["protection_daily"]
        try:
            daily[day_key] = max(0.0, float(daily.get(day_key, 0))) + elapsed
        except (TypeError, ValueError):
            daily[day_key] = elapsed

        today = date.today()
        current_week_start = today - timedelta(days=(today.weekday() + 1) % 7)
        self.settings["protection_daily"] = {
            key: value for key, value in daily.items()
            if isinstance(key, str) and key >= current_week_start.isoformat()
        }
        self._refresh_protection_chart()

        minute_bucket = int(now // 60)
        if minute_bucket != self._protection_last_saved_minute:
            self._save_settings()
            self._protection_last_saved_minute = minute_bucket

    def _update_ui_state(self, status: ConnectionStatus, has_cap: bool, logged_in: bool):
        # A poll that was in flight when a transition started carries a stale status:
        # applying it would fight _set_busy and make the status line flicker.
        # A stuck transition must not freeze the dashboard forever.
        if getattr(self, "is_busy", False) and time.time() - getattr(self, "_busy_since", 0.0) < 90:
            return False

        self.current_status = status
        self.is_connected = status.connected

        self._record_protection_time()
        self.banner_cap.set_revealed(not has_cap)

        # Active relay node
        self.row_relay.set_subtitle(status.server or "None")

        # Update location label based on active status
        if status.connected:
            if hasattr(self, "lbl_loc_name") and status.country:
                name_text = f"{status.city}, {status.country}" if status.city else status.country
                self.lbl_loc_name.set_label(name_text)
                self.lbl_loc_name.set_tooltip_text(None)
        else:
            if hasattr(self, "lbl_loc_name") and hasattr(self, "selected_label"):
                self.lbl_loc_name.set_label(self.selected_label)
                self.lbl_loc_name.set_tooltip_text(None)

        self._update_location_diurnal(status.server if status.connected else None)

        # Telemetry
        self.lbl_down.set_label(status.transfer_down or "0.0 MB")
        self.lbl_up.set_label(status.transfer_up or "0.0 MB")
        self.lbl_tunnel.set_label(status.server or ("Inactive" if not status.connected else "Active"))

        # Virtual IP update
        if hasattr(self, "lbl_ip_val"):
            if status.connected:
                virtual_ip = status.ip or "10.64.0.1"
                self.lbl_ip_val.set_label(virtual_ip)
                self.lbl_ip_val.set_tooltip_text(f"Virtual IP: {virtual_ip}")
                self.lbl_ip_val.remove_css_class("disabled")
                self.lbl_ip_val.add_css_class("active")
            else:
                self.lbl_ip_val.set_label("Unprotected")
                self.lbl_ip_val.set_tooltip_text("Unprotected - Physical IP exposed")
                self.lbl_ip_val.remove_css_class("active")
                self.lbl_ip_val.add_css_class("disabled")

        # Update bottom details card
        ks_setting = bool(self.settings.get("kill_switch", False))
        if hasattr(self, "switch_main_ks") and not getattr(self, "_ks_syncing", False):
            self._ks_syncing = True
            try:
                if self.switch_main_ks.get_active() != ks_setting:
                    self.switch_main_ks.set_active(ks_setting)
            finally:
                self._ks_syncing = False

        if hasattr(self, "lbl_ks_status"):
            self.lbl_ks_status.remove_css_class("mullvad-details-badge")
            self.lbl_ks_status.remove_css_class("mullvad-details-badge-armed")
            self.lbl_ks_status.remove_css_class("mullvad-details-badge-off")
            if ks_setting:
                if self.settings.get("hard_kill_switch", False):
                    self.lbl_ks_status.set_label("Strict")
                    self.lbl_ks_status.remove_css_class("disabled")
                    self.lbl_ks_status.remove_css_class("armed")
                    self.lbl_ks_status.add_css_class("active")
                elif status.connected and self.backend.is_killswitch_active():
                    self.lbl_ks_status.set_label("Active")
                    self.lbl_ks_status.remove_css_class("disabled")
                    self.lbl_ks_status.remove_css_class("armed")
                    self.lbl_ks_status.add_css_class("active")
                else:
                    self.lbl_ks_status.set_label("Armed")
                    self.lbl_ks_status.remove_css_class("disabled")
                    self.lbl_ks_status.remove_css_class("active")
                    self.lbl_ks_status.add_css_class("armed")
            else:
                self.lbl_ks_status.set_label("Disabled")
                self.lbl_ks_status.remove_css_class("active")
                self.lbl_ks_status.remove_css_class("armed")
                self.lbl_ks_status.add_css_class("disabled")
        if hasattr(self, "lbl_dns_status"):
            self.lbl_dns_status.set_label("Protected" if self.settings.get("dns_leak_shield", True) else "Off")
        # Update official flag webp icon
        if status.connected and status.server:
            srv_cc = (status.server.split("-")[0]).lower()
            self._update_flag_icon(cc_override=srv_cc)
        else:
            self._update_flag_icon()

        # Check unexpected drop if Kill Switch is active
        if self.should_be_connected and not status.connected and not self.is_busy:
            self.should_be_connected = False
            if logged_in and self.switch_killswitch.get_active():
                self.backend.enable_killswitch(hard=self.settings.get("hard_kill_switch", False))
                self._show_toast("⚠️ Kill Switch: Tunnel dropped! Traffic protected.")
                if self.switch_autoreconnect.get_active():
                    self._connect_vpn()

        # Status transition
        self.is_connected = status.connected
        if hasattr(self, "tray") and self.tray:
            self.tray.update_status(status.connected, status.server)

        self.banner_box.remove_css_class("mullvad-banner-connecting")
        self.banner_box.remove_css_class("mbvpn-hero-connecting")
        if status.connected:
            self.banner_box.remove_css_class("mullvad-banner-unsecured")
            self.banner_box.remove_css_class("mbvpn-hero-unsecured")
            self.banner_box.add_css_class("mullvad-banner-secured")
            self.banner_box.add_css_class("mbvpn-hero-secured")
            if hasattr(self, "cyber_shield"):
                self.cyber_shield.set_mode("protected")
            if hasattr(self, "world_map"):
                self.world_map.set_target(server=status.server or "", city=status.city or "", country=status.country or "")
                self.world_map.set_state("protected")
            if hasattr(self, "header_icon"):
                self.header_icon.set_from_icon_name("channel-secure-symbolic")

            self._set_status_message("Tunnel active", "#7dd3fc")
            if hasattr(self, "lbl_status_desc"):
                self.lbl_status_desc.set_tooltip_text("WireGuard tunnel active")
        else:
            self.banner_box.remove_css_class("mullvad-banner-secured")
            self.banner_box.remove_css_class("mbvpn-hero-secured")
            self.banner_box.add_css_class("mullvad-banner-unsecured")
            self.banner_box.add_css_class("mbvpn-hero-unsecured")
            if hasattr(self, "cyber_shield"):
                self.cyber_shield.set_mode("unprotected")
            if hasattr(self, "world_map"):
                if hasattr(self, "selected_target"):
                    self.world_map.set_target(server=self.selected_target)
                self.world_map.set_state("unprotected")
            if hasattr(self, "header_icon"):
                self.header_icon.set_from_icon_name("channel-insecure-symbolic")

            if not logged_in:
                self._set_status_message("Sign in to activate VPN", "#fb7185")
            else:
                self._set_status_message("VPN is off", "#fb7185")

        self._sync_connect_button(logged_in=logged_in)
        self._repaint_status()

        return False

    def _on_toggle_clicked(self, _):
        if getattr(self, "is_busy", False):
            # While the tunnel is being negotiated the control doubles as Cancel
            if getattr(self, "_busy_mode", "") == "connecting" and not self._cancel_connect_requested:
                self._cancel_connecting()
            return
        if self.is_connected:
            self._disconnect_vpn()
        else:
            self._connect_vpn()

    def _cancel_connecting(self):
        """Ask the in-flight connect to abort; the tunnel is torn down when the attempt returns."""
        self._cancel_connect_requested = True
        self._set_status_message("Cancelling\u2026", dot_color="#38bdf8")
        if hasattr(self, "lbl_status_desc"):
            self.lbl_status_desc.set_tooltip_text("Aborting the connection attempt")
        self._sync_connect_button()
        self._repaint_status()

    def _connect_vpn(self):
        if not self.backend.is_logged_in():
            self.should_be_connecting = False
            self.should_be_connected = False
            self._set_busy(False)
            self._show_account_dialog()
            return

        target = self.selected_target
        if not target or target in ("fastest", "auto"):
            target = "sg"

        self._cancel_connect_requested = False
        self.should_be_connecting = True
        self._set_busy(True, message="Initializing WireGuard cryptographic keys...", title="CONNECTING...", mode="connecting")

        def report_progress(message):
            def update_label():
                if self.should_be_connecting and self.lbl_status_desc:
                    # Detail only in the tooltip; the pill stays a compact "Connecting…"
                    self.lbl_status_desc.set_tooltip_text(message)
                return False
            GLib.idle_add(update_label)

        def worker():
            success = False
            msg = ""
            hard_killswitch = self.settings.get("hard_kill_switch", False)
            try:
                if self.backend.is_killswitch_active() and not hard_killswitch:
                    self.backend.disable_killswitch()

                success, msg = self.backend.connect(
                    target,
                    hard_killswitch=hard_killswitch,
                    progress_callback=report_progress,
                )
                self.should_be_connecting = False
                if self._cancel_connect_requested:
                    # The attempt could not be interrupted mid-flight, so undo it immediately
                    if success:
                        try:
                            self.backend.disconnect(hard_killswitch=hard_killswitch)
                        except Exception:
                            pass
                    success = False
                    msg = "Connection cancelled"
                    self.should_be_connected = False
                elif success:
                    self.should_be_connected = True
                    if self.settings.get("kill_switch") and not hard_killswitch:
                        self.backend.enable_killswitch(
                            bypass_apps=self.settings.get("bypass_apps", []),
                            bypass_antigravity=self.settings.get("bypass_antigravity", True),
                            hard=False,
                        )
                else:
                    self.should_be_connected = False
            except Exception as e:
                success = False
                msg = str(e)
                self.should_be_connecting = False
                self.should_be_connected = False
            finally:
                try:
                    status = self.backend.get_status()
                except Exception:
                    status = ConnectionStatus(connected=success)
                try:
                    has_cap, _ = self.backend.check_capabilities()
                except Exception:
                    has_cap = False
                logged_in = self.backend.is_logged_in()
                cancelled = self._cancel_connect_requested

                def finish():
                    self._cancel_connect_requested = False
                    self._set_busy(False)
                    self._update_ui_state(status, has_cap, logged_in)
                    if not success and not cancelled:
                        self._show_toast(f"Connection error: {msg}")
                    return False

                GLib.idle_add(finish)

        threading.Thread(target=worker, daemon=True).start()

    def _disconnect_vpn(self):
        self.should_be_connected = False
        self._set_busy(True, message="Releasing virtual IP address...", title="DISCONNECTING...", mode="disconnecting")

        def step2():
            if getattr(self, "is_busy", False) and hasattr(self, "lbl_status_desc"):
                self.lbl_status_desc.set_tooltip_text("Safely closing WireGuard tunnel\u2026")
            return False

        GLib.timeout_add(500, step2)

        def worker():
            hard_killswitch = self.settings.get("hard_kill_switch", False)
            success, msg = self.backend.disconnect(hard_killswitch=hard_killswitch)
            # backend.disconnect already handles KS cleanup via _killswitch_active cache.
            # No extra is_killswitch_active() subprocess needed here.

            status = self.backend.get_status()
            has_cap, _ = self.backend.check_capabilities()
            logged_in = self.backend.is_logged_in()

            def finish():
                self._set_busy(False)
                self._update_ui_state(status, has_cap, logged_in)
                if not success:
                    self._show_toast(f"Disconnect failed: {msg}")
                return False

            GLib.idle_add(finish)

        threading.Thread(target=worker, daemon=True).start()

    def _fix_capabilities(self):
        if self.backend.has_firewall_capabilities() and self.backend.check_capabilities()[0]:
            return
        binary = os.path.realpath(self.backend.binary_path)
        firewall_bin = os.path.realpath(self.backend.firewall_path) if self.backend.is_firewall_available() else None
        if firewall_bin:
            cmd = ["pkexec", "setcap", "cap_net_admin,cap_net_raw+eip", binary, "cap_net_admin,cap_net_raw+eip", firewall_bin]
        else:
            cmd = ["pkexec", "setcap", "cap_net_admin,cap_net_raw+eip", binary]
        self._set_busy(True, "Applying network capabilities...")

        def worker():
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                success = (res.returncode == 0)
                msg = res.stderr.strip() or res.stdout.strip()
            except Exception as e:
                success = False
                msg = str(e)

            def finish():
                self._set_busy(False)
                if success:
                    if self.settings.get("kill_switch"):
                        self.backend.enable_killswitch(hard=self.settings.get("hard_kill_switch", False))
                else:
                    self._show_toast(f"Setup: {msg or 'Cancelled'}")
                self.refresh_async()
                return False

            GLib.idle_add(finish)

        threading.Thread(target=worker, daemon=True).start()

    def _show_server_browser_modal(self):
        """
        World Server Browser:
        Displays all 36 countries, 62 cities, and 149 individual servers with instant fuzzy search.
        """
        dialog = Adw.Window(transient_for=self, modal=True)
        dialog.add_css_class("mullvad-window")
        dialog.set_title("VPN Locations and Servers")
        dialog.set_default_size(380, 580)
        dialog.set_size_request(360, 520)
        dialog.set_resizable(False)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)
        dialog.set_content(vbox)

        # Header
        header = Adw.HeaderBar()
        win_title = Adw.WindowTitle(title="Locations", subtitle="62 Locations • 36 Countries • 150+ Servers")
        header.set_title_widget(win_title)
        vbox.append(header)

        # Search Bar
        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Search country, city, or tag...")
        vbox.append(search_entry)

        # Category Filter Tabs (Clean Segmented Bar, No Scrollbar)
        cat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        cat_box.add_css_class("cat-box-container")
        cat_box.set_homogeneous(True)
        cat_box.set_margin_top(2)
        cat_box.set_margin_bottom(4)
        vbox.append(cat_box)

        categories = [
            ("all", "All", "All Locations", "62 Locations Worldwide • 150+ Physical RAM Servers"),
            ("streaming", "Streaming", "Streaming Optimized", "Netflix, Hulu, BBC, Prime, Disney+"),
            ("torrenting", "Torrenting", "P2P / BitTorrent", "High-Throughput Swarms & Privacy Jurisdictions"),
            ("fastest", "Fastest", "Lowest Latency", "Direct Tier-1 Internet Exchanges"),
            ("privacy", "Privacy", "Offshore & Non-14-Eyes", "Strong Constitutional Secrecy"),
        ]

        active_cat = ["all"]
        cat_buttons = {}

        # Scroller
        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        vbox.append(scroller)

        list_box = Gtk.ListBox()
        list_box.add_css_class("boxed-list")
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scroller.set_child(list_box)

        # Load all countries from backend
        countries = self.backend.get_locations()

        items = []

        # 1. Fastest / Auto Row
        row_auto = Adw.ActionRow()
        row_auto.set_title("Fastest Location (Recommended)")
        row_auto.set_subtitle("Automatically picks lowest latency server")
        icon_auto = Gtk.Image.new_from_icon_name("network-wireless-symbolic")
        icon_auto.set_pixel_size(18)
        row_auto.add_prefix(icon_auto)

        btn_auto = Gtk.Button(label="Connect")
        btn_auto.add_css_class("suggested-action")
        btn_auto.set_valign(Gtk.Align.CENTER)

        def on_auto(_):
            self.selected_target = "sg"
            self.selected_label = "Fastest Server (Singapore)"
            self.selected_flag = "🇸🇬"
            self.selected_sub = "Optimal Server"
            self.lbl_flag.set_label(self.selected_flag)
            self.lbl_loc_name.set_label(self.selected_label)
            self.lbl_loc_sub.set_label(self.selected_sub)
            self._update_flag_icon()
            self.settings["last_target"] = self.selected_target
            self.settings["last_label"] = self.selected_label
            self.settings["last_flag"] = self.selected_flag
            self.settings["last_sub"] = self.selected_sub
            self._add_recent_server("sg", "Fastest Server (Singapore)", "🇸🇬", "Optimal Server")
            dialog.close()
            self._connect_vpn()

        btn_auto.connect("clicked", on_auto)
        row_auto.add_suffix(btn_auto)
        list_box.append(row_auto)
        items.append((row_auto, "fastest auto recommended lowest latency", None, ["all", "fastest"], {"all": "Automatically picks lowest latency server", "fastest": "Optimal latency &amp; ping routing across global nodes"}))

        # 2. Iterate through all countries
        for c in countries:
            expander = Adw.ExpanderRow()
            total_servers = sum(len(ct.servers) for ct in c.cities)
            city_str = "1 city" if len(c.cities) == 1 else f"{len(c.cities)} cities"
            srv_str = "1 server" if total_servers == 1 else f"{total_servers} servers"
            default_sub = f"{city_str} • {srv_str}"
            expander.set_title(c.name)
            expander.set_subtitle(default_sub)

            lbl_f = Gtk.Label(label=c.flag)
            lbl_f.add_css_class("badge-flag")
            expander.add_prefix(lbl_f)

            # Quick connect to country default
            btn_cntry = Gtk.Button(label="Connect")
            btn_cntry.set_valign(Gtk.Align.CENTER)
            btn_cntry.add_css_class("flat")

            def on_cntry_click(_, code=c.code, name=c.name, flag=c.flag):
                self.selected_target = code
                self.selected_label = name
                self.selected_flag = flag
                self.selected_sub = "Optimal Server"
                self.lbl_flag.set_label(self.selected_flag)
                self.lbl_loc_name.set_label(self.selected_label)
                self.lbl_loc_sub.set_label(self.selected_sub)
                self._update_flag_icon()
                if hasattr(self, "world_map"):
                    self.world_map.set_target(server=code)
                self.settings["last_target"] = self.selected_target
                self.settings["last_label"] = self.selected_label
                self.settings["last_flag"] = self.selected_flag
                self.settings["last_sub"] = self.selected_sub
                self._add_recent_server(code, name, flag, self.selected_sub)
                dialog.close()
                self._connect_vpn()

            btn_cntry.connect("clicked", on_cntry_click)
            expander.add_suffix(btn_cntry)

            # Add each city as child row
            for ct in c.cities:
                city_row = Adw.ActionRow()
                city_row.set_title(ct.name)
                ct_srv_str = "1 server" if len(ct.servers) == 1 else f"{len(ct.servers)} servers"
                city_row.set_subtitle(f"Code: {ct.code} • {ct_srv_str}")

                btn_city = Gtk.Button(label="Connect")
                btn_city.set_valign(Gtk.Align.CENTER)
                btn_city.add_css_class("flat")

                def on_city_click(_, code=ct.code, c_name=c.name, ct_name=ct.name, flag=c.flag):
                    self.selected_target = code
                    self.selected_label = f"{ct_name}, {c_name}"
                    self.selected_flag = flag
                    self.selected_sub = "Optimal Server"
                    self.lbl_flag.set_label(self.selected_flag)
                    self.lbl_loc_name.set_label(self.selected_label)
                    self.lbl_loc_sub.set_label(self.selected_sub)
                    self._update_flag_icon()
                    if hasattr(self, "world_map"):
                        self.world_map.set_target(server=code)
                    self.settings["last_target"] = self.selected_target
                    self.settings["last_label"] = self.selected_label
                    self.settings["last_flag"] = self.selected_flag
                    self.settings["last_sub"] = self.selected_sub
                    self._add_recent_server(code, self.selected_label, flag, self.selected_sub)
                    dialog.close()
                    self._connect_vpn()

                btn_city.connect("clicked", on_city_click)
                city_row.add_suffix(btn_city)
                expander.add_row(city_row)

            list_box.append(expander)
            search_corpus = f"{c.name} {c.code} {c.region} {c.streaming_tag} {c.torrenting_tag} {c.privacy_tag} {c.fastest_tag} " + " ".join(ct.name + " " + ct.code for ct in c.cities)
            cat_tag_map = {
                "all": default_sub,
                "streaming": f"{c.streaming_tag}" if c.streaming_tag else default_sub,
                "torrenting": f"{c.torrenting_tag}" if c.torrenting_tag else default_sub,
                "fastest": f"{c.fastest_tag}" if c.fastest_tag else default_sub,
                "privacy": f"{c.privacy_tag}" if c.privacy_tag else default_sub,
            }
            items.append((expander, search_corpus.lower(), expander, c.categories, cat_tag_map))

        # Filter callback supporting both category pills and text search
        def update_filter():
            current_cat = active_cat[0]
            query = search_entry.get_text().strip().lower()
            for item in items:
                widget = item[0]
                corpus = item[1]
                exp = item[2]
                item_cats = item[3]
                tag_map = item[4]

                cat_match = (current_cat == "all") or (current_cat in item_cats)
                query_match = (not query) or (query in corpus)

                is_visible = cat_match and query_match
                widget.set_visible(is_visible)

                if is_visible:
                    # Update subtitle dynamically based on category
                    if isinstance(tag_map, dict):
                        sub_text = tag_map.get(current_cat, tag_map.get("all", ""))
                        widget.set_subtitle(GLib.markup_escape_text(sub_text) if sub_text else "")
                    if exp and query:
                        exp.set_expanded(True)
                    elif exp and not query:
                        exp.set_expanded(False)

            # Update category buttons styling
            for cid, btn in cat_buttons.items():
                if cid == current_cat:
                    btn.add_css_class("cat-pill-active")
                else:
                    btn.remove_css_class("cat-pill-active")

            # Update Window Subtitle
            for cid, _, _, csub in categories:
                if cid == current_cat:
                    win_title.set_subtitle(csub)
                    break

        for cat_id, label, cat_title, cat_subtitle in categories:
            btn = Gtk.Button(label=label)
            btn.add_css_class("cat-pill")
            if cat_id == "all":
                btn.add_css_class("cat-pill-active")
            def on_cat_click(_, cid=cat_id):
                active_cat[0] = cid
                update_filter()
            btn.connect("clicked", on_cat_click)
            cat_buttons[cat_id] = btn
            cat_box.append(btn)

        search_entry.connect("search-changed", lambda _: update_filter())
        dialog.present()
        return dialog

    def _show_account_dialog(self):
        """Account, subscription status, and license activation modal"""
        dialog = Adw.Window(transient_for=self, modal=True)
        dialog.add_css_class("mullvad-window")
        dialog.set_title("Account and License")
        dialog.set_default_size(380, 560)
        dialog.set_size_request(360, 500)
        dialog.set_resizable(False)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        dialog.set_content(main_box)

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Account and License"))
        main_box.append(header)

        # Toast overlay for account dialog
        dlg_toast_overlay = Adw.ToastOverlay()
        main_box.append(dlg_toast_overlay)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        dlg_toast_overlay.set_child(scroller)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        content.set_margin_top(12)
        content.set_margin_bottom(20)
        content.set_margin_start(14)
        content.set_margin_end(14)
        scroller.set_child(content)

        # Get account details from backend
        acct = self.backend.get_account_details()
        is_auth = self.backend.is_logged_in()

        # 1. Subscription Overview Group
        group_sub = Adw.PreferencesGroup()
        group_sub.set_title("Subscription Overview")
        group_sub.set_description("Active license and plan details")

        # Plan Row
        row_plan = Adw.ActionRow()
        row_plan.set_title("Subscription Plan")
        row_plan.set_subtitle(acct.get("plan", "Malwarebytes Privacy VPN"))
        row_plan.add_prefix(Gtk.Image.new_from_icon_name("security-high-symbolic" if is_auth else "security-low-symbolic"))
        group_sub.add(row_plan)

        # Status Row
        row_status = Adw.ActionRow()
        row_status.set_title("License Status")
        row_status.set_subtitle(f"Licensed • Active ({acct.get('status', 'Active')})" if is_auth else "Not Activated")
        row_status.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic" if is_auth else "dialog-warning-symbolic"))
        group_sub.add(row_status)

        # Expiry Row
        if is_auth and acct.get("expiry_formatted"):
            row_exp = Adw.ActionRow()
            row_exp.set_title("Expiration Date")
            days_str = f" ({acct['days_remaining']} days remaining)" if acct.get("days_remaining") is not None else ""
            row_exp.set_subtitle(f"{acct['expiry_formatted']}{days_str}")
            row_exp.add_prefix(Gtk.Image.new_from_icon_name("x-office-calendar-symbolic"))
            group_sub.add(row_exp)

        # License Key Row (with copy button)
        if acct.get("license_key"):
            row_key = Adw.ActionRow()
            row_key.set_title("License Key")
            key_val = acct["license_key"]
            row_key.set_subtitle(key_val)
            row_key.add_prefix(Gtk.Image.new_from_icon_name("dialog-password-symbolic"))

            btn_copy_key = Gtk.Button(icon_name="edit-copy-symbolic")
            btn_copy_key.set_valign(Gtk.Align.CENTER)
            btn_copy_key.add_css_class("flat")
            btn_copy_key.set_tooltip_text("Copy License Key")

            def on_copy_key(_):
                clipboard = self.get_display().get_clipboard()
                clipboard.set(key_val)
                dlg_toast_overlay.add_toast(Adw.Toast.new("License Key copied to clipboard"))

            btn_copy_key.connect("clicked", on_copy_key)
            row_key.add_suffix(btn_copy_key)
            group_sub.add(row_key)

        content.append(group_sub)

        # 2. Activation / Switch License Group
        group_login = Adw.PreferencesGroup()
        group_login.set_title("Switch or Update License")
        group_login.set_description(
            "Enter a new 25-character Master License Key or 6-character MB-code."
        )

        entry_code = Adw.EntryRow()
        entry_code.set_title("New License Key / MB-Code")
        entry_code.set_show_apply_button(False)
        group_login.add(entry_code)

        btn_act = Gtk.Button(label="Apply License")
        btn_act.add_css_class("suggested-action")
        btn_act.set_margin_top(8)

        def on_act_click(_):
            val = entry_code.get_text().strip()
            if not val:
                dlg_toast_overlay.add_toast(Adw.Toast.new("Please enter a license key or MB-code"))
                return
            btn_act.set_sensitive(False)
            btn_act.set_label("Authenticating with Malwarebytes...")

            def worker():
                success, msg = self.backend.activate_with_key_or_code(val)

                def finish():
                    btn_act.set_sensitive(True)
                    btn_act.set_label("Apply License")
                    if success:
                        dialog.close()
                        self.refresh_async()
                    else:
                        dlg_toast_overlay.add_toast(Adw.Toast.new(f"Activation failed: {msg}"))
                    return False

                GLib.idle_add(finish)

            threading.Thread(target=worker, daemon=True).start()

        btn_act.connect("clicked", on_act_click)
        group_login.add(btn_act)
        content.append(group_login)

        # 4. Logout / Release Seat
        if is_auth:
            group_logout = Adw.PreferencesGroup()
            group_logout.set_title("Deactivate and Release Seat")
            group_logout.set_description("Frees this device slot on your Malwarebytes subscription.")

            btn_logout = Gtk.Button(label="Deactivate Device and Free Seat")
            btn_logout.add_css_class("destructive-action")

            def on_logout(_):
                btn_logout.set_sensitive(False)

                def worker():
                    success, msg = self.backend.logout(hard_killswitch=self.settings.get("hard_kill_switch", False))

                    def finish():
                        btn_logout.set_sensitive(True)
                        if success:
                            self.should_be_connected = False
                            self.should_be_connecting = False
                            self.is_connected = False
                            self._set_busy(False)
                            dialog.close()
                            self.refresh_async()
                        else:
                            dlg_toast_overlay.add_toast(Adw.Toast.new(f"Logout error: {msg}"))
                        return False

                    GLib.idle_add(finish)

                threading.Thread(target=worker, daemon=True).start()

            btn_logout.connect("clicked", on_logout)
            group_logout.add(btn_logout)
            content.append(group_logout)

        dialog.present()
        return dialog


class MbVpnApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.paradoxbyte.mbvpn",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MbVpnWindow(application=self)
        win.present()


def main():
    GLib.set_prgname("org.paradoxbyte.mbvpn")
    GLib.set_application_name("MalwarebytesVPN")
    Gtk.Window.set_default_icon_name("mbvpn")
    app = MbVpnApplication()
    return app.run([sys.argv[0]])


if __name__ == "__main__":
    sys.exit(main())
