# Compatibility shim: keep old import paths working after moving to engines.muscle.typography_core
import importlib, sys as _sys
_mod = importlib.import_module("engines.muscle.typography_core")
_sys.modules[__name__] = _mod
