# Compatibility shim: keep old import paths working after moving to engines.muscle.video_multicam
import importlib, sys as _sys
_mod = importlib.import_module("engines.muscle.video_multicam")
_sys.modules[__name__] = _mod
