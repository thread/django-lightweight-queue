from .utils import load_all_tasks

try:
    load_all_tasks()
except RuntimeError:
    # Initialisation tasks in latest versions of Django get run in AppConfig
    # (see apps.py).
    pass
