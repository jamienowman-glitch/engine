# Compatibility shim: keep old import paths working after moving to engines.muscle.boq_costing
import importlib, sys as _sys
_mod = importlib.import_module("engines.muscle.boq_costing")
_sys.modules[__name__] = _mod
