param(
  [Parameter(Mandatory=$true)][string]$Root,
  [Parameter(Mandatory=$true)][int]$QwenWatcherPid,
  [int]$PollSeconds = 60,
  [int]$MaxWaitSeconds = 86400
)

$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = Join-Path $Root "logs\command_outputs"
$testDir = Join-Path $Root "logs\tests"
New-Item -ItemType Directory -Force -Path $logDir, $testDir | Out-Null
$chainLog = Join-Path $logDir "chain_gemma_after_qwen_$stamp.log"
$chainExit = Join-Path $testDir "chain_gemma_after_qwen_$stamp.exitcode"

function Write-ChainLog {
  param([string]$Message)
  Add-Content -LiteralPath $chainLog -Value "$(Get-Date -Format o) $Message"
}

function Latest-QwenWatcherExitFile {
  Get-ChildItem -Path $testDir -Filter "watch_stage1_postprocess_qwen35_4b_*.exitcode" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
}

try {
  Write-ChainLog "chain_started qwen_watcher_pid=$QwenWatcherPid"
  $started = Get-Date
  while (Get-Process -Id $QwenWatcherPid -ErrorAction SilentlyContinue) {
    $elapsed = [int]((Get-Date) - $started).TotalSeconds
    if ($elapsed -gt $MaxWaitSeconds) {
      Write-ChainLog "timeout waiting for qwen watcher after ${elapsed}s"
      Set-Content -LiteralPath $chainExit -Value 124
      exit 124
    }
    Start-Sleep -Seconds $PollSeconds
  }

  $watchExitFile = Latest-QwenWatcherExitFile
  if (-not $watchExitFile) {
    Write-ChainLog "qwen watcher exited but no qwen watcher exit file was found"
    Set-Content -LiteralPath $chainExit -Value 11
    exit 11
  }
  $qwenPostCode = (Get-Content -LiteralPath $watchExitFile.FullName -Raw).Trim()
  Write-ChainLog "qwen_watcher_exit_file=$($watchExitFile.FullName) code=$qwenPostCode"
  if ($qwenPostCode -ne "0") {
    Write-ChainLog "qwen postprocess was not successful; gemma chain skipped"
    Set-Content -LiteralPath $chainExit -Value 12
    exit 12
  }

  $env:WSLENV = "OPENAI_API_KEY/u"
  $gemmaTrainLog = Join-Path $logDir "chain_triggered_gemma_stage1_training_$stamp.log"
  Write-ChainLog "gemma_training_started log=$gemmaTrainLog"
  wsl.exe bash -lc "source ~/miniconda3/etc/profile.d/conda.sh && conda activate clearread-llama-lora && cd /mnt/c/Users/Aufb/Desktop/fit5120/iteration3/new-model/fine_tune_sweep && bash scripts/run_qlora_training_with_fallback.sh gemma4_e4b_it stage1_anchor_r32_lr2e4 5 0.0002 32 64 0.05 2 4 1 8" > $gemmaTrainLog 2>&1
  $gemmaTrainCode = $LASTEXITCODE
  Write-ChainLog "gemma_training_finished code=$gemmaTrainCode"
  if ($gemmaTrainCode -ne 0) {
    Set-Content -LiteralPath $chainExit -Value $gemmaTrainCode
    exit $gemmaTrainCode
  }

  $gemmaPostLog = Join-Path $logDir "chain_triggered_gemma_stage1_postprocess_$stamp.log"
  Write-ChainLog "gemma_postprocess_started log=$gemmaPostLog"
  wsl.exe bash -lc "source ~/miniconda3/etc/profile.d/conda.sh && conda activate clearread-llama-lora && cd /mnt/c/Users/Aufb/Desktop/fit5120/iteration3/new-model/fine_tune_sweep && bash scripts/postprocess_stage1_candidate.sh gemma4_e4b_it stage1_val50_gemma4_anchor_20260512" > $gemmaPostLog 2>&1
  $gemmaPostCode = $LASTEXITCODE
  Write-ChainLog "gemma_postprocess_finished code=$gemmaPostCode"
  Set-Content -LiteralPath $chainExit -Value $gemmaPostCode
  exit $gemmaPostCode
} catch {
  Write-ChainLog "chain_failed $($_.Exception.GetType().FullName): $($_.Exception.Message)"
  Set-Content -LiteralPath $chainExit -Value 1
  exit 1
}
