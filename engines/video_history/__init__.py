# Compatibility shim: keep old import paths working after moving to engines.muscle.video_history
import importlib, sys as _sys
_mod = importlib.import_module("engines.muscle.video_history")
_sys.modules[__name__] = _mod
