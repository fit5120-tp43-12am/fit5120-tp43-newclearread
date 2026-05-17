param(
  [Parameter(Mandatory=$true)][int]$OldPid,
  [int]$PollSeconds = 30,
  [int]$MaxWaitSeconds = 21600
)

$ErrorActionPreference = "Stop"
$Root = "C:\Users\Aufb\Desktop\fit5120\iteration3\new-model\fine_tune_sweep\phase2_48h_search"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogDir = Join-Path $Root "logs\command_outputs"
$TestDir = Join-Path $Root "logs\tests"
$DecisionDir = Join-Path $Root "logs\decisions"
New-Item -ItemType Directory -Force -Path $LogDir, $TestDir, $DecisionDir | Out-Null

$SwitchLog = Join-Path $LogDir "compressed_switch_after_phi_$Stamp.log"
$SwitchExit = Join-Path $TestDir "compressed_switch_after_phi_$Stamp.exitcode"
$CompressedLog = Join-Path $LogDir "compressed_orchestrator_$Stamp.log"
$CompressedExit = Join-Path $TestDir "compressed_orchestrator_$Stamp.exitcode"
$CompressedPid = Join-Path $TestDir "compressed_orchestrator_$Stamp.pid"

function Write-SwitchLog {
  param([string]$Message)
  Add-Content -LiteralPath $SwitchLog -Value "$(Get-Date -Format o) $Message"
}

function Get-PostprocessExit {
  Get-ChildItem -Path $TestDir -Filter "postprocess_phi4_mini_instruct_phase2_r64_a128_lr1e4_*.exitcode" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
}

function Stop-ProcessTree {
  param([int]$RootPid)
  $children = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $RootPid }
  foreach ($child in $children) {
    Stop-ProcessTree -RootPid ([int]$child.ProcessId)
  }
  $proc = Get-Process -Id $RootPid -ErrorAction SilentlyContinue
  if ($proc) {
    Write-SwitchLog "stopping pid=$RootPid name=$($proc.ProcessName)"
    Stop-Process -Id $RootPid -Force -ErrorAction SilentlyContinue
  }
}

try {
  Write-SwitchLog "watcher_started old_pid=$OldPid"
  $started = Get-Date
  $postExit = $null
  while (-not $postExit) {
    $elapsed = [int]((Get-Date) - $started).TotalSeconds
    if ($elapsed -gt $MaxWaitSeconds) {
      Write-SwitchLog "timeout waiting for Phi r64 postprocess after ${elapsed}s"
      Set-Content -LiteralPath $SwitchExit -Value 124
      exit 124
    }
    $postExit = Get-PostprocessExit
    if (-not $postExit) {
      Start-Sleep -Seconds $PollSeconds
    }
  }

  $code = (Get-Content -LiteralPath $postExit.FullName -Raw).Trim()
  Write-SwitchLog "phi_r64_postprocess_exit_file=$($postExit.FullName) code=$code"
  if ($code -ne "0") {
    Write-SwitchLog "Phi r64 postprocess did not finish cleanly; compressed takeover will not start automatically."
    Set-Content -LiteralPath $SwitchExit -Value 12
    exit 12
  }

  $note = Join-Path $DecisionDir "superseded_by_compressed_plan_$Stamp.md"
  @(
    "# Superseded by Compressed Plan",
    "",
    "- Current Phi r64 postprocess completed successfully.",
    "- The previous full matrix orchestrator is being stopped at the safe boundary.",
    "- The compressed orchestrator will run Llama and Ministral challenger runs with hard kill rules.",
    "- No files are deleted."
  ) | Set-Content -LiteralPath $note -Encoding UTF8

  Stop-ProcessTree -RootPid $OldPid
  Start-Sleep -Seconds 5

  $env:WSLENV = "OPENAI_API_KEY/u"
  $WslCommand = "source ~/miniconda3/etc/profile.d/conda.sh && conda activate clearread-llama-lora && cd /mnt/c/Users/Aufb/Desktop/fit5120/iteration3/new-model/fine_tune_sweep/phase2_48h_search && python scripts/run_phase2_compressed_search.py"
  $PsCommand = "`$env:WSLENV='OPENAI_API_KEY/u'; wsl.exe bash -lc '$WslCommand' > '$CompressedLog' 2>&1; `$code=`$LASTEXITCODE; Set-Content -LiteralPath '$CompressedExit' -Value `$code; exit `$code"
  $process = Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $PsCommand) -WindowStyle Hidden -PassThru
  Set-Content -LiteralPath $CompressedPid -Value $process.Id
  Write-SwitchLog "compressed_orchestrator_started pid=$($process.Id) log=$CompressedLog"
  Set-Content -LiteralPath $SwitchExit -Value 0
  exit 0
} catch {
  Write-SwitchLog "switch_failed $($_.Exception.GetType().FullName): $($_.Exception.Message)"
  Set-Content -LiteralPath $SwitchExit -Value 1
  exit 1
}
