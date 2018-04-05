#!/usr/bin/env python
# -*- coding: utf-8 -*-
from . import __version__

#: meta data for opkg
PACKAGE_META = {
    "package": "pert-belly-hack-backend",
    "upstream_version": __version__,
    "epoch": 2,
    "target_root_path": "OpenWebif",
    "description": "backend component providing XML and RESTful APIs",
    "conflicts": "enigma2-plugin-extensions-openwebif",
}
