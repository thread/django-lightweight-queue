from .utils import import_all_submodules

try:
    import_all_submodules('tasks')
except RuntimeError:
    # Initialisation tasks in latest versions of Django get run in AppConfig
    # (see apps.py).
    pass
