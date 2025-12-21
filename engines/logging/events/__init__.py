import sys

# Avoid conflicts with stdlib `logging` package by aliasing this package under the engines namespace.
sys.modules.setdefault("logging.events", sys.modules[__name__])
