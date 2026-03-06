---
name: "unreal-dev-power"
displayName: "Unreal Engine Dev Power"
description: "AI-assisted development for deadline-cloud-for-unreal-engine - implement designs, fix bugs, build, lint, test"
keywords: ["unreal", "ue5", "deadline", "build", "test", "lint", "integration", "adaptor"]
author: "AWS Deadline Cloud Team"
---

# Unreal Engine Dev Power

## Start of Session

Prompt user:
```
What would you like to do?
1. Implement a design doc (from docs/design/)
2. Fix a bug
3. Other development task
```

**If implementing a design doc:**
- Ask which design doc in `docs/design/`
- Read the design doc and its implementation plan
- Guide user through tasks in order
- For each task: implement → add unit tests → run tests → lint

**If fixing a bug or other task:**
- Ask user to describe the issue or task
- Proceed with development cycle

## Your Role

Implement code changes with tests. Execute build, lint, and test commands. Monitor output, report results, identify errors, suggest fixes.

**Important:** `pytest` does not work directly. Always use `hatch run test` or `hatch run e2e`.

## Development Cycle

For each task or change:
1. Implement the change
2. Add unit tests
3. Run tests: `hatch run test`
4. Format: `hatch run fmt`
5. Lint: `hatch run lint`

After milestone or final change:
6. Build: `hatch build`
7. Integration test: `hatch run e2e -s`

## Steering Files

- **build-and-test.md** - Commands reference, integration testing, and error handling
