# Compatibility shim: keep old import paths working after moving to engines.muscle.audio_field_to_samples
import importlib, sys as _sys
_mod = importlib.import_module("engines.muscle.audio_field_to_samples")
_sys.modules[__name__] = _mod
