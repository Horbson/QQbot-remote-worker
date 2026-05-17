# -*- coding: utf-8 -*-
"""
Mode system entry point.

All available modes are discovered at import time and then validated before the
global ModeManager instance is created.
"""
from botpy import logging

from .manager import ModeManager
from .plugin_loader import discover_modes, validate_mode

_log = logging.get_logger(__name__)

discovered_modes = discover_modes()
valid_modes = {}

for mode_name, mode_config in discovered_modes.items():
    if validate_mode(mode_name, mode_config):
        valid_modes[mode_name] = mode_config
    else:
        _log.error(f"Mode {mode_name} validation failed, skipped.")

modes = valid_modes
mode_manager = ModeManager(modes)

_log.info(f"Mode system initialized. loaded={len(modes)}, modes={list(modes.keys())}")
