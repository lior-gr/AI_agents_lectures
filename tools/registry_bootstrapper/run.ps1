param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ScriptDir ".venv"
$RequirementsFile = Join-Path $ScriptDir "requirements.txt"
$PythonScript = Join-Path $ScriptDir "registry_bootstrapper.py"

function Ensure-Venv {
  param([string]$Path)

  if (Test-Path -LiteralPath $Path) {
    return
  }

  $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
  if ($PyLauncher) {
    & py -3 -m venv $Path
  } else {
    $Python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $Python) {
      throw "Python was not found on PATH. Install Python 3.10+ and retry."
    }
    & python -m venv $Path
  }

  if ($LASTEXITCODE -ne 0) {
    throw "Failed to create venv at $Path"
  }
}

Ensure-Venv -Path $VenvDir

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
  throw "Venv python executable was not found: $VenvPython"
}

& $VenvPython -m pip install --upgrade pip | Out-Host
if ($LASTEXITCODE -ne 0) {
  throw "pip upgrade failed"
}

if (Test-Path -LiteralPath $RequirementsFile) {
  & $VenvPython -m pip install -r $RequirementsFile | Out-Host
  if ($LASTEXITCODE -ne 0) {
    throw "pip requirements install failed"
  }
}

& $VenvPython $PythonScript @Args
exit $LASTEXITCODE
