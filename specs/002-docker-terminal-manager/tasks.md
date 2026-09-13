# Tasks: Docker terminal manager

## Phase 1: Setup and foundation
- [x] T001 Lock runtime/dev/tool dependencies in pyproject.toml and uv.lock (FR-007).
- [x] T002 Repair baseline lint/type failures in src, tests and scripts without weakening gates (FR-007).

## Phase 2: US1 container runtime
- [x] T003 Add tests for HTTP startup/config validation/health in tests/test_runtime.py (FR-005, FR-006).
- [x] T004 Implement HTTP server and health probe in src/mijobs/mcp_server.py and healthcheck.py (FR-005).
- [x] T005 Add Dockerfile, compose.yaml, .dockerignore, .env.example and ignored .env; persistent volume and isolated CI target (FR-001, FR-002, FR-004, FR-007).

## Phase 3: US2 terminal operations
- [x] T006 Add operation and UI tests in tests/test_manager.py for lifecycle, errors, redaction and menu exit (FR-003, FR-006).
- [x] T007 Implement Rich manager and fixed Compose command routing in src/mijobs/manager.py (FR-003, FR-006).

## Phase 4: US3 maintenance and convergence
- [x] T008 Consolidate root README and Makefile around Docker, .env, MCP and persistence; include Docker recovery advice (FR-002, FR-008).
- [x] T009 Run strict CI and real container lifecycle/MCP/TUI/persistence checks, fix defects, record evidence in validation.md (FR-001 through FR-008, SC-001 through SC-004).

## Dependencies and implementation strategy
T001 -> T002 -> T003 -> T004 -> T005 -> T006 -> T007 -> T008 -> T009. All work is sequential except read-only research. US1 supplies the image/runtime for US2. US3 documents validated contracts. Test the runtime and operation contracts before their implementation, then run full Linux container validation. Existing baseline specs remain intact.

## Phase 5: Accepted agent integration
- [x] T010 Add and test shared Compose network and optional deploy/render_kubernetes.py, document separate agent wiring and future Kubernetes workflow (FR-009, FR-010).
