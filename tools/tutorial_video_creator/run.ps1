param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ScriptDir ".venv"
$RequirementsFile = Join-Path $ScriptDir "requirements.txt"
$PythonScript = Join-Path $ScriptDir "tutorial_video_creator.py"

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

function Resolve-Ffmpeg {
  $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
  if ($ffmpeg) {
    return $ffmpeg.Source
  }

  if ($env:LOCALAPPDATA) {
    $wingetLink = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\ffmpeg.exe"
    if (Test-Path -LiteralPath $wingetLink) {
      return $wingetLink
    }

    $wingetPattern = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\Gyan.FFmpeg_*\ffmpeg-*\bin\ffmpeg.exe"
    $wingetCandidate = Get-ChildItem -Path $wingetPattern -File -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 1
    if ($wingetCandidate) {
      return $wingetCandidate.FullName
    }
  }

  return $null
}

function Ensure-Ffmpeg {
  $resolved = Resolve-Ffmpeg
  if ($resolved) {
    return $resolved
  }

  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if ($winget) {
    Write-Host "ffmpeg not found. Attempting install via winget..."
    winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements | Out-Host
  }

  $resolved = Resolve-Ffmpeg
  if (-not $resolved) {
    throw "ffmpeg was not found and auto-install did not succeed. Install ffmpeg or pass --ffmpeg-path."
  }

  return $resolved
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

$FfmpegPath = Ensure-Ffmpeg
$HasFfmpegArg = $false
foreach ($arg in $Args) {
  if ($arg -eq "--ffmpeg-path" -or $arg -eq "-FfmpegPath") {
    $HasFfmpegArg = $true
    break
  }
}

$FinalArgs = @()
if (-not $HasFfmpegArg -and $FfmpegPath) {
  $FinalArgs += @("--ffmpeg-path", $FfmpegPath)
}
$FinalArgs += $Args

& $VenvPython $PythonScript @FinalArgs
exit $LASTEXITCODE
