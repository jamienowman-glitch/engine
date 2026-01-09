import warnings

# We don't export the router here to avoid duplicate routes, or to ensure the old route is gone.
# If we wanted to keep the old route working but redirecting, we could do that, but the requirement
# is to fail if the old route is called.
# So we export nothing useful for routing.

warnings.warn("engines.blackboard_store.routes is deprecated. Use engines.run_memory.routes instead.", DeprecationWarning, stacklevel=2)
