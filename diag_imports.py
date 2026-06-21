import importlib
import sys
import time

modules = [
    "app",
    "app.core.config",
    "app.core.database",
    "app.core.exception_handlers",
    "app.core.middleware",
    "app.core.limiter",
    "app.core.ws_auth",
    "app.modules.auth.controller",
    "app.modules.disasters.controller",
    "app.modules.admin.controller",
    "app.modules.social.controller",
    "app.modules.tasks.controller",
    "app.modules.resources.controller",
    "app.modules.notifications.controller",
    "app.modules.incoming_alerts.schemas",
    "app.modules.incoming_alerts.models",
    "app.modules.incoming_alerts.repository",
    "app.modules.incoming_alerts.service",
    "app.modules.incoming_alerts.controller",
    "app.websockets.manager",
    "app.main",
]

for m in modules:
    print(f"-> importing {m}", flush=True)
    t0 = time.time()
    try:
        importlib.import_module(m)
        elapsed = time.time() - t0
        print(f"<- imported {m} ({elapsed:.3f}s)", flush=True)
    except Exception as e:
        print(f"!! error importing {m}: {e!r}", flush=True)
        raise

print("done", flush=True)
