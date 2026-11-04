"""HTTP route groups of the Visable backend (Phase 6 of the rebuild, ADR-013).

Each module exposes ``build_router(pb) -> APIRouter``; ``pb`` is the ``paradiso_backend`` facade,
which owns configuration, schemas, state and helpers and includes the routers in document order.
"""
