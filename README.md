# Universal MCP Tool Framework

A reusable Python foundation for Model Context Protocol tools. The framework centralises registration, discovery, permissions, operation-mode separation, structured errors, logging, configuration, health/status output, and extension conventions.

## Design Boundary

The framework is an **MCP server foundation**, not a generic shell, filesystem controller, or policy engine. Tools are registered explicitly and run through one permission boundary.

| Operation mode | Default | Requirement |
|---|---:|---|
| `read` | Enabled | Tool must be registered as read-only. |
| `write` | Disabled | Configuration enables `write` and caller has the declared scope. |
| `execute` | Disabled | Configuration enables `execute` and caller has the declared scope. |

A tool must pass **both** checks: its operation mode is enabled and its required scopes are present in the execution context.

## Included Surface

| Capability | Implementation |
|---|---|
| Standard MCP server | `server.py` exposes `mcp` for the official MCP Python SDK. |
| Registration and discovery | `ToolRegistry` owns explicit registration and returns public tool metadata. |
| Permission model | `ToolRuntime` enforces enabled operation modes and per-tool scopes. |
| Read/write/execute separation | `OperationMode` is mandatory for every tool. Read-only is the default. |
| Error handling and logging | Every execution returns a structured result envelope; rejected and failed calls are logged. |
| Configuration | `config.example.json` controls server identity, enabled modes, and log level. |
| Health/status | `framework_health`, `framework_status`, and `framework_discover_tools` are MCP tools. |
| Example tools | Time read, simulated note write, and simulated check execute tools demonstrate every mode. |
| Extension path | One decorator registers each new tool; the runtime supplies all common controls. |

## Requirements

- Python 3.10+
- The official MCP Python SDK, pinned to `mcp==2.0.0`

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -p "test_*.py"
```

Start the server through the MCP SDK:

```bash
mcp run server.py
```

For interactive development with MCP Inspector:

```bash
mcp dev server.py
```

## Configuration

Copy and modify the example only when non-read operations are required.

```json
{
  "server_name": "Universal MCP Tool Framework",
  "enabled_modes": ["read"],
  "log_level": "INFO"
}
```

`read` is the only default mode. To permit a registered write tool, add `write`; to permit a registered execution tool, add `execute`. Enabling a mode does **not** bypass required per-tool scopes.

Start the server with a selected configuration file:

```bash
UNIVERSAL_MCP_CONFIG=config.json mcp run server.py
```

## Add a Tool

1. Choose one operation mode.
2. Declare every required scope.
3. Register the handler through `ToolRegistry`.
4. Add a test for discovery, allowed execution, and rejection paths.
5. Expose a thin MCP handler only if the tool belongs in the public server surface.

```python
from universal_mcp.models import OperationMode
from universal_mcp.registry import ToolRegistry

registry = ToolRegistry()

@registry.register(
    name="inventory_get_item",
    description="Return one inventory item by stable identifier.",
    mode=OperationMode.READ,
    required_scopes={"inventory:read"},
)
def inventory_get_item(item_id: str) -> dict[str, str]:
    return {"item_id": item_id}
```

Call it through `ToolRuntime.execute()` so the common permission, logging, and error contract always applies.

## Result Contract

All runtime executions produce this stable envelope:

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

Rejected and failed requests use `ok: false` and a machine-readable error code such as `tool_not_found`, `permission_denied`, or `tool_execution_failed`.

## Repository Structure

```text
.
├── config.example.json
├── pyproject.toml
├── server.py
├── src/universal_mcp/
│   ├── config.py
│   ├── examples.py
│   ├── models.py
│   ├── registry.py
│   ├── runtime.py
│   └── server.py
└── tests/test_framework.py
```

## Validation

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The test suite verifies discovery, default read access, write/execute denial by default, scope enforcement, structured errors, status output, and JSON configuration.

## Universal Project Scaffolding Toolkit

The repository also provides `umcp-scaffold`, a controlled generator for repeatable Python project starts.

| Project template | Generated capability |
|---|---|
| `python-library` | Installable `src/` package, unit-test starter, development/production configuration, setup scripts, documentation, project state, and Git initialization. |
| `mcp-tool` | Everything in `python-library`, plus a standard MCP server entry point and the pinned MCP SDK dependency. |

Create a fully initialized project. By default, the generator creates a local Git repository, creates an isolated `.venv`, installs local dependencies, and validates the generated project.

```bash
umcp-scaffold create "My Project" ./my-project --type mcp-tool
```

Validate a generated project later:

```bash
umcp-scaffold validate ./my-project
```

Every generated project receives `.project-state.json` with its schema version, name, package name, template type, lifecycle state, Git/dependency flags, creation time, and last validation state. The generator rejects non-empty target directories rather than overwriting a project.
