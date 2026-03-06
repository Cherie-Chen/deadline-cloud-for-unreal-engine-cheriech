# Build and Test Reference

**Important:** Always use `hatch run test`, not `pytest` directly.

## Commands

### Build
```bash
hatch build                             # Build Python wheel
python scripts/build_plugin.py --ueversion {VERSION}  # Build Unreal plugin
```

### Test
```bash
hatch run test                                          # All unit tests
hatch run test test/deadline_adaptor_for_unreal/unit/   # Specific directory
hatch run test -k "test_render"                         # Pattern match
hatch run e2e -s                                        # Integration tests
```

### Integration Test Details

Prerequisites: AWS credentials, Unreal Engine installed, test project.

Environment variables:
```powershell
$env:UE_ENGINE_DIR = "C:\Program Files\Epic Games\UE_{VERSION}"
$env:DEADLINE_LOG_LEVEL = "DEBUG"
$env:UNREAL_TEST_PROJECT = "C:\Path\To\TestProject.uproject"
```

Tests in `test/end_to_end/`:
- `conftest.py` — AWS resource creation (farms, queues, fleets), UE discovery
- `test_create_job.py` — Job creation tests
- `test_worker_agent.py` — Worker agent tests

### Debugging
```powershell
$env:DEADLINE_LOG_LEVEL = "DEBUG"
Get-Content "$env:LOCALAPPDATA\UnrealEngine\{VERSION}\Saved\Logs\UnrealEditor.log" -Tail 100
python -m deadline.unreal_adaptor --help
```

### Unreal Spec Tests (Manual)

Runs Deadline Cloud plugin's Unreal Automation Tests from within Unreal Engine.

**One-time setup** — Enable these plugins in UE project:
- Automation Driver Tests
- Automation Utilities
- Python Automation Tests

**Steps:**
1. Install plugin with test content:
   ```bash
   python scripts/build_plugin.py --install --test
   ```
2. Launch Unreal Engine → Tools → Test Automation
3. In Session Frontend → Automation tab
4. Search "Deadline", select all tests under "DeadlineCloud"
5. Click ">" to run

Call out these steps for user to follow up on manually.

### Lint & Format
```bash
hatch run fmt                           # Format code
hatch run lint                          # Run linter
```

### Install to Unreal Engine
```bash
python scripts/build_plugin.py --ueversion {VERSION} --install
```

## Error Handling

### Hatch Not Found
```bash
pip install hatch
```

### Plugin Build Fails
Verify: `where.exe msbuild` and UE installation path.

### Import Errors
```bash
pip install -e .
```
