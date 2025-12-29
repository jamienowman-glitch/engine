# Compatibility shim: keep old import paths working after moving to engines.muscle.audio_fx_chain
import importlib, sys as _sys
_mod = importlib.import_module("engines.muscle.audio_fx_chain")
_sys.modules[__name__] = _mod
