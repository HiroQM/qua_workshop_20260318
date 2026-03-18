QM Workshop Environment Setup (with `uv`)
This guide sets up a Python 3.11 environment with the required QM packages using `uv`.
---
🚀 Prerequisites
Internet connection
macOS / Linux / Windows (PowerShell)
---
🐧 macOS / Linux
1. Install `uv`
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
2. Create project and environment
```bash
mkdir qm-workshop
cd qm-workshop

uv python install 3.11
uv venv qmenv --python 3.11
source qmenv/bin/activate
```
3. Install dependencies
```bash
uv pip install --prerelease=allow qm-qua==1.2.6 qualang-tools==0.21.1 qm-saas==1.1.7
```
---
🪟 Windows (PowerShell)
1. Install `uv`
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```
> ⚠️ Close and reopen PowerShell after installation
---
2. Create project and environment
```powershell
mkdir qm-workshop
cd qm-workshop

uv python install 3.11
uv venv qmenv --python 3.11
qmenv\Scripts\Activate.ps1
```
---
3. Install dependencies
```powershell
uv pip install --prerelease=allow qm-qua==1.2.6 qualang-tools==0.21.1 qm-saas==1.1.7
```
---
⚠️ Windows Execution Policy Issue
If activation is blocked:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
Then retry:
```powershell
qmenv\Scripts\Activate.ps1
```
---
✅ Verify Installation
```bash
python --version
```
Expected:
```
Python 3.11.x
```
Check packages:
```bash
pip list
```
---
💡 Notes
The environment is isolated (`qmenv`)
`uv` is used for faster installs and better dependency resolution
`--prerelease=allow` ensures compatibility with QM packages
---
🧹 Optional: Deactivate Environment
```bash
deactivate
```