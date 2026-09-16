# Architecture Rules

These rules keep the codebase easy to navigate, test, and change. Use the words
module, interface, seam, adapter, depth, leverage, and locality consistently.

## Repository Layout

- The repository root contains only project entrypoints, project configuration,
  documentation, scripts, tests, source, resources, models, and runtime data.
- Runtime Python packages live under `src/`. Do not add business modules at the
  repository root.
- Model artifacts live under `models/`. Notebooks live under `notebooks/`.
- Agent prompts and skill resources live under `resources/skills/`.
- Operational scripts live under `scripts/` and call public package interfaces.
- `data/` is for runtime data such as local SQLite session storage.

## Module Design

- A business module must expose a small, clear interface and hide meaningful
  implementation behind it.
- Tests should cross the same interface callers use. If a test needs to reach
  through the interface, reconsider the module shape.
- Apply the deletion test before extracting a module: deleting a valuable module
  should concentrate complexity back into multiple callers, not make complexity
  disappear.
- Create a seam only when behavior actually varies across adapters, or when the
  seam materially improves locality and testability.

## Dependency Direction

- `app.medication` is the medication consultation module. Keep orchestration,
  ports, Long Chau, and Neo4j adapters local to this module.
- `app.chat` is the chat streaming runtime module. It should use medication
  behavior only through the ADK tool seam.
- `core.schema` is the Knowledge Graph schema module. It must not depend on
  FastAPI, ADK, HTTP clients, or runtime configuration.
- `config` contains settings and infrastructure configuration only. It must not
  contain business rules.
- Adapters may depend inward on models and ports; domain-facing modules should
  not depend outward on concrete infrastructure clients unless that client is the
  module's own adapter.

## Documentation

- README and architecture docs must reflect the current code path. If the active
  model, path layout, route shape, or runtime dependency changes, update docs in
  the same change.
- Any refactor that moves public paths must update tests, Dockerfile, package
  discovery, and local run commands together.
