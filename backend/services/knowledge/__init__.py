"""Waymaker Knowledge Platform.

Canonical, versioned, source-grounded immigration knowledge with a human
review lifecycle, coverage-aware retrieval, a privacy-minimized learning loop
and a persistent evaluation corpus. See docs/ai/WAYMAKER_KNOWLEDGE_PLATFORM.md.

Module map:
    models       vocabulary (states, reasons, intents) + boundary schemas
    store        SQLite connection, migrations, transactions, audit log
    lifecycle    centralized transition rules (mirrored by DB triggers)
    repository   the only module that writes knowledge rows
    conflicts    deterministic conflict / update classification
    review       review queue, actions, transactional publish, impact
    ingestion    proposal validation, dry-run / validate / apply
    adapters     reference ingestion paths over existing repository data
    diff         source-version diff (ADDED / REMOVED / CHANGED / UNCHANGED)
    retrieval    retrieve_knowledge(status, procedure, intent, as_of)
    understanding / coverage / guard   the answer decision path
    privacy / learning                 observations, gaps, feedback
    evals        persistent eval corpus + offline runner
    runtime      facade used by /api/ask, the operator API and the CLI
    api          operator (authenticated) + public feedback endpoints
"""
