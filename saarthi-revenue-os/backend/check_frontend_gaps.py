import sys
import json
from pathlib import Path
from app.main import app

# Quick script to list all backend routes
routes = []
for route in app.routes:
    if hasattr(route, "methods"):
        path = route.path
        methods = route.methods - {"OPTIONS"}
        if methods:
            routes.append(f"{','.join(methods)} {path}")

routes.sort()
print("Backend API Routes:")
for r in routes:
    print(f"  {r}")
