---
name: unreal-dev-setup
version: 1.0.0
displayName: Unreal Engine Dev Setup
description: AI-guided automated setup for deadline-cloud-for-unreal-engine on Windows - validates prerequisites, builds packages, installs dependencies, and configures environment
keywords: ["unreal", "ue5", "deadline", "setup", "build", "install", "environment", "development", "hatch", "openjd", "windows"]
author: AWS Deadline Cloud Team
---

# Unreal Engine Dev Setup Power

AI-guided automated development environment setup for deadline-cloud-for-unreal-engine project.

**Platform:** Windows only

## What This Power Does

The AI agent automates the complete development environment setup:
- Verifies Windows OS
- Validates system requirements (GPU, Windows Long Paths, Build Tools, Deadline Cloud Monitor)
- Handles repository setup (clone or use existing)
- Detects and validates Unreal Engine installation
- Installs Hatch and dependencies
- Builds and installs the C++ plugin and Python packages
- Verifies environment variables
- Generates reference documentation

**Only manual step:** Enabling the plugin in Unreal Engine (final step)

## AI Agent Behavior

The agent will:
- **Automate** all possible steps
- **Prompt** only when user input is required (fork URL, UE version, custom paths)
- **Inform** when manual intervention is needed (installing prerequisites)
- **Validate** all inputs before proceeding
- **Report** progress and errors clearly

## Prerequisites

Required (agent will verify):
- Python 3.9+
- Unreal Engine 5.4+ (default: 5.6)
- Windows OS
- Visual Studio 2019/2022 with C++ tools
- Git
- Deadline Cloud Monitor
- NVIDIA GPU with drivers

## User Prompts

The agent will ask for:
1. **Repository location** (default: current directory + subfolder)
2. **Fork URL** (only if cloning new)
3. **Unreal Engine version** (default: 5.6)
4. **Custom UE path** (only if not found at default location)

## After Setup

The agent will instruct you to complete the final manual step:

**Enable the plugin in Unreal Engine:**
https://aws-deadline.github.io/unreal-engine/setup-submitter/#submitter-installation-complete

This covers:
1. Opening Unreal Engine
2. Enabling the Deadline Cloud plugin
3. Configuring plugin settings
4. Submitting a test render

## Reference Files

- **setup-guide.md** - Complete AI agent workflow
- **troubleshooting.md** - Common issues and solutions
