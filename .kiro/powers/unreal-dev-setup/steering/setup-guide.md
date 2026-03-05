# Unreal Engine Dev Setup Guide

AI agent workflow for automating deadline-cloud-for-unreal-engine development environment setup.

**Platform:** Windows only

## AI Agent Responsibilities

The AI agent should:
1. **Verify Windows OS first** - Abort if not Windows
2. Automate all steps except final UE plugin enablement
3. Only prompt when information is required or manual intervention needed

## Setup Workflow

### Step 0: Verify Windows OS

**AI Action:** Check operating system

```powershell
$PSVersionTable.Platform
# or
[System.Environment]::OSVersion.Platform
```

**If not Windows:**
- Display error: "This setup only supports Windows. Unreal Engine development for Deadline Cloud requires Windows OS."
- Abort setup

### Step 1: Verify GPU and Drivers

**AI Action:** Check GPU availability and drivers

```powershell
Get-WmiObject Win32_VideoController | Where-Object {$_.Name -like "*NVIDIA*"}
nvidia-smi
```

**If GPU not found or nvidia-smi fails:**
- Inform user GPU/drivers are required
- Provide installation links:
  - Local: https://www.nvidia.com/Download/index.aspx
  - EC2: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-nvidia-driver.html#nvidia-GRID-driver
- Wait for user confirmation before continuing

### Step 2: Verify Windows Long Paths

**AI Action:** Check and enable if possible

```powershell
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled"
```

**If not enabled:**
- Attempt to enable (requires admin):
  ```powershell
  New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
  ```
- If fails, instruct user to run as admin or follow: https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation

### Step 3: Verify Python Installation

**AI Action:** Check Python version

```powershell
python --version
```

**If not found or version < 3.9:**
- Attempt to install Python 3.12 using winget:
  ```powershell
  winget install Python.Python.3.12 --scope machine
  ```
- If winget fails, inform user to manually install:
  - Download from: https://www.python.org/downloads/
  - Install for all users
  - Wait for user confirmation before continuing

### Step 4: Verify Build Tools

**AI Action:** Check for Visual Studio and MSBuild

```powershell
where.exe msbuild
Get-ChildItem "C:\Program Files\Microsoft Visual Studio" -Directory
```

**If not found:**
- Inform user Visual Studio with C++ tools is required
- Provide link: https://visualstudio.microsoft.com/
- Required components:
  - Workload: "Desktop development with C++"
  - Individual Components: MSVC build tools (match UE version)
  - Individual Components: .NET Framework SDK (4.6.1 or 4.8.1)
- Verify compatibility: https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-visual-studio-development-environment-for-cplusplus-projects-in-unreal-engine
- Wait for user confirmation before continuing

### Step 5: Verify Deadline Cloud Monitor

**AI Action:** Check for Deadline CLI and Monitor

```powershell
# Check Deadline CLI
deadline --version

# Check Deadline Cloud Monitor
Test-Path "$env:LOCALAPPDATA\DeadlineCloudMonitor\DeadlineCloudMonitor.exe"
```

**If both found:**
- Display: "Deadline Cloud Monitor installed (CLI version: [VERSION])"
- Continue

**If either not found:**
- Inform user Deadline Cloud Monitor is required for job submission
- Installation instructions:
  - Download from: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/submitter.html#install-deadline-cloud-monitor
  - Default install location: `C:\Users\{username}\AppData\Local\DeadlineCloudMonitor`
  - Note: Installing Deadline Cloud Monitor also installs the Deadline CLI
- Wait for user confirmation before continuing

### Step 6: Setup Repository

**AI Action:** Check if repository exists at default location

```powershell
$repoPath = Join-Path (Get-Location) "deadline-cloud-for-unreal-engine"
Test-Path $repoPath
```

**If exists:**
- Verify it's a git repository:
  ```powershell
  cd $repoPath
  git remote -v
  ```
- Display: "Using existing repository at $repoPath"
- Continue to Step 7

**If not exists:**
- Prompt for fork URL:
  ```
  Please enter your deadline-cloud-for-unreal-engine GitHub fork URL:
  (e.g., https://github.com/YOUR-USERNAME/deadline-cloud-for-unreal-engine.git)
  ```
- Clone to default location:
  ```powershell
  git clone -b mainline [FORK_URL] $repoPath
  cd $repoPath
  ```

### Step 7: Determine Unreal Engine Version

**AI Action:** Check for installed UE versions at default location

```powershell
Get-ChildItem "C:\Program Files\Epic Games" -Directory | Where-Object {$_.Name -match "^UE_\d+\.\d+$"} | Sort-Object Name -Descending
```

**If UE versions found:**
- Use the newest version (first in sorted list)
- Display: "Found Unreal Engine {VERSION} at default location"
- Continue to Step 8

**If no UE versions found:**
- Prompt user:
  ```
  No Unreal Engine installation found at default location.
  
  Options:
  1. Install Unreal Engine (recommended versions: 5.4, 5.5, 5.6, 5.7)
  2. Specify custom installation path
  
  To install Unreal Engine:
  - Download Epic Games Launcher: https://www.unrealengine.com/download
  - Install desired UE version (5.4+)
  
  Enter 'custom' to specify a custom path, or press Enter after installing UE:
  ```
- If user enters 'custom', prompt for path and validate:
  ```powershell
  Test-Path "$USER_PATH\Engine\Binaries\Win64\UnrealEditor.exe"
  ```
- If user presses Enter, re-check for installations

### Step 8: Install Hatch

**AI Action:** Check and install if needed

```powershell
hatch --version
```

**If not installed:**

```powershell
python -m pip install hatch
$scriptsPath = "C:\Users\$env:USERNAME\AppData\Roaming\Python\Python311\Scripts"
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$scriptsPath", [EnvironmentVariableTarget]::User)
hatch --version
```

### Step 9: Build and Install Plugin

**AI Action:** Execute build command

```powershell
python scripts/build_plugin.py --ueversion {VERSION} --install
# Or with custom path:
python scripts/build_plugin.py --ueversion {VERSION} --engine-root "{CUSTOM_UE_PATH}" --install
```

**AI Action:** Monitor build output and report progress

### Step 10: Verify Environment Variables

**AI Action:** Check PATH

```powershell
$env:PATH -split ';' | Select-String "Python"
$env:PATH -split ';' | Select-String "Epic Games"
```

**If missing:**
- Inform user which paths are missing
- Provide link: https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/docs/user_guide/setup-submitter.md#environment-setup

### Step 11: Display Installation Summary

**AI Action:** Show installation summary

```
✓ Automated Setup Complete!

Installed:
- Python: [VERSION]
- Hatch: [VERSION]
- Unreal Engine: [VERSION] at [PATH]
- Plugin built and installed to: [PATH]

### Step 12: Enable Plugin in Unreal Engine (MANUAL)

**User Action Required:**

The plugin is installed but must be enabled manually in Unreal Engine.

Follow the instructions at:
https://aws-deadline.github.io/unreal-engine/setup-submitter/#submitter-installation-complete

This will guide you through:
1. Opening Unreal Engine
2. Enabling the Deadline Cloud plugin
3. Configuring plugin settings
4. Submitting a test render to verify setup

**After completing Step 12, your development environment is fully ready!**

## Key Principles

1. **Automate everything possible** - Only stop for required user input or manual steps
2. **Clear prompts** - Make it obvious what the user needs to provide
3. **Validate inputs** - Check paths, URLs, versions before proceeding
4. **Informative output** - Show what's happening at each step
5. **Handle errors gracefully** - Provide clear next steps when something fails
6. **Single manual step** - Only the final UE plugin enablement requires manual work
