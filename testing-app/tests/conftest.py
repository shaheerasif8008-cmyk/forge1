import os
import sys

# Force testing mode for SQLite in-memory DB
os.environ.setdefault("TESTING", "1")

# Ensure project root and parent (repo root) are on sys.path so `import app` and `shared` both resolve
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(PROJECT_ROOT)
SHARED_PKG_ROOT = os.path.join(REPO_ROOT, "shared")
for p in (PROJECT_ROOT, REPO_ROOT, SHARED_PKG_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)
