param(
  [Parameter(Mandatory=$true)][string]$Root,
  [Parameter(Mandatory=$true)][int]$GemmaChainPid,
  [int]$PollSeconds = 120,
  [int]$MaxWaitSeconds = 604800
)

$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = Join-Path $Root "logs\command_outputs"
$testDir = Join-Path $Root "logs\tests"
New-Item -ItemType Directory -Force -Path $logDir, $testDir | Out-Null
$chainLog = Join-Path $logDir "chain_stage2_stage3_after_stage1_$stamp.log"
$chainExit = Join-Path $testDir "chain_stage2_stage3_after_stage1_$stamp.exitcode"

function Write-ChainLog {
  param([string]$Message)
  Add-Content -LiteralPath $chainLog -Value "$(Get-Date -Format o) $Message"
}

function Latest-GemmaChainExitFile {
  Get-ChildItem -Path $testDir -Filter "chain_gemma_after_qwen_*.exitcode" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
}

try {
  Write-ChainLog "stage2_stage3_chain_started gemma_chain_pid=$GemmaChainPid"
  $started = Get-Date
  while (Get-Process -Id $GemmaChainPid -ErrorAction SilentlyContinue) {
    $elapsed = [int]((Get-Date) - $started).TotalSeconds
    if ($elapsed -gt $MaxWaitSeconds) {
      Write-ChainLog "timeout waiting for gemma chain after ${elapsed}s"
      Set-Content -LiteralPath $chainExit -Value 124
      exit 124
    }
    Start-Sleep -Seconds $PollSeconds
  }

  $gemmaExitFile = Latest-GemmaChainExitFile
  if (-not $gemmaExitFile) {
    Write-ChainLog "gemma chain exited but no chain exit file was found"
    Set-Content -LiteralPath $chainExit -Value 11
    exit 11
  }

  $gemmaCode = (Get-Content -LiteralPath $gemmaExitFile.FullName -Raw).Trim()
  Write-ChainLog "gemma_chain_exit_file=$($gemmaExitFile.FullName) code=$gemmaCode"
  if ($gemmaCode -ne "0") {
    Write-ChainLog "stage1 did not complete successfully; stage2/stage3 skipped"
    Set-Content -LiteralPath $chainExit -Value 12
    exit 12
  }

  $env:WSLENV = "OPENAI_API_KEY/u"
  $stageLog = Join-Path $logDir "chain_triggered_stage2_stage3_$stamp.log"
  Write-ChainLog "stage2_stage3_started log=$stageLog"
  wsl.exe bash -lc "source ~/miniconda3/etc/profile.d/conda.sh && conda activate clearread-llama-lora && cd /mnt/c/Users/Aufb/Desktop/fit5120/iteration3/new-model/fine_tune_sweep && python scripts/summarize_stage1_results.py && python scripts/select_stage2_top_models.py && python scripts/create_stage3_run_matrix.py && python scripts/run_stage3_matrix.py --continue-on-failure" > $stageLog 2>&1
  $stageCode = $LASTEXITCODE
  Write-ChainLog "stage2_stage3_finished code=$stageCode"
  Set-Content -LiteralPath $chainExit -Value $stageCode
  exit $stageCode
} catch {
  Write-ChainLog "stage2_stage3_chain_failed $($_.Exception.GetType().FullName): $($_.Exception.Message)"
  Set-Content -LiteralPath $chainExit -Value 1
  exit 1
}
