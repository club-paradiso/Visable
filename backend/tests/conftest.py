"""Backend test configuration.

Backend tests use an in-memory knowledge store so no test ever reads or
writes the developer's local knowledge database (backend/var/knowledge/),
and every test module starts from the same committed seed.
"""
import os

os.environ.setdefault("WAYMAKER_KNOWLEDGE_DB", ":memory:")
