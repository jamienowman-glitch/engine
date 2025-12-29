# Compatibility shim: keep old import paths working after moving to engines.muscle.cad_viewer
import importlib, sys as _sys
_mod = importlib.import_module("engines.muscle.cad_viewer")
_sys.modules[__name__] = _mod
