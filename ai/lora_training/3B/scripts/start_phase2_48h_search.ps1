param(
  [switch]$SkipPreflight,
  [switch]$SkipFinalBenchmark
)

$ErrorActionPreference = "Stop"
$Root = "C:\Users\Aufb\Desktop\fit5120\iteration3\new-model\fine_tune_sweep\phase2_48h_search"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogDir = Join-Path $Root "logs\command_outputs"
$TestDir = Join-Path $Root "logs\tests"
New-Item -ItemType Directory -Force -Path $LogDir, $TestDir | Out-Null

$LogPath = Join-Path $LogDir "phase2_orchestrator_$Stamp.log"
$ExitPath = Join-Path $TestDir "phase2_orchestrator_$Stamp.exitcode"
$PidPath = Join-Path $TestDir "phase2_orchestrator_$Stamp.pid"
$Script = Join-Path $Root "scripts\run_phase2_48h_search.py"

$Args = @()
if ($SkipPreflight) { $Args += "--skip-preflight" }
if ($SkipFinalBenchmark) { $Args += "--skip-final-benchmark" }
$ArgText = ($Args -join " ")

$env:WSLENV = "OPENAI_API_KEY/u"
$WslCommand = "source ~/miniconda3/etc/profile.d/conda.sh && conda activate clearread-llama-lora && cd /mnt/c/Users/Aufb/Desktop/fit5120/iteration3/new-model/fine_tune_sweep/phase2_48h_search && python scripts/run_phase2_48h_search.py $ArgText"
$PsCommand = "`$env:WSLENV='OPENAI_API_KEY/u'; wsl.exe bash -lc '$WslCommand' > '$LogPath' 2>&1; `$code=`$LASTEXITCODE; Set-Content -LiteralPath '$ExitPath' -Value `$code; exit `$code"

$Process = Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $PsCommand) -WindowStyle Hidden -PassThru
Set-Content -LiteralPath $PidPath -Value $Process.Id

[pscustomobject]@{
  status = "started"
  pid = $Process.Id
  log_path = $LogPath
  exit_path = $ExitPath
  pid_path = $PidPath
  root = $Root
} | ConvertTo-Json
