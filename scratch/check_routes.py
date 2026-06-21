"""Print all registered routes for quick verification."""
from app.main import create_app

app = create_app()
for r in app.routes:
    path = getattr(r, "path", None)
    methods = getattr(r, "methods", None)
    if path:
        label = ",".join(sorted(methods)) if methods else "WS"
        print(f"{label:<25} {path}")
