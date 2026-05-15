param(
  [Parameter(Mandatory=$true)][string]$Root,
  [Parameter(Mandatory=$true)][string]$CandidateKey,
  [Parameter(Mandatory=$true)][string]$TrainingExitFile,
  [Parameter(Mandatory=$true)][string]$JudgeRunId,
  [int]$PollSeconds = 60,
  [int]$MaxWaitSeconds = 43200
)

$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = Join-Path $Root "logs\command_outputs"
$testDir = Join-Path $Root "logs\tests"
New-Item -ItemType Directory -Force -Path $logDir, $testDir | Out-Null
$watchLog = Join-Path $logDir "watch_stage1_postprocess_${CandidateKey}_$stamp.log"
$watchExit = Join-Path $testDir "watch_stage1_postprocess_${CandidateKey}_$stamp.exitcode"

function Write-WatchLog {
  param([string]$Message)
  $line = "$(Get-Date -Format o) $Message"
  Add-Content -LiteralPath $watchLog -Value $line
}

try {
  Write-WatchLog "watch_started candidate=$CandidateKey training_exit_file=$TrainingExitFile judge_run_id=$JudgeRunId"
  $started = Get-Date
  while (-not (Test-Path -LiteralPath $TrainingExitFile)) {
    $elapsed = [int]((Get-Date) - $started).TotalSeconds
    if ($elapsed -gt $MaxWaitSeconds) {
      Write-WatchLog "timeout waiting for training exit file after ${elapsed}s"
      Set-Content -LiteralPath $watchExit -Value 124
      exit 124
    }
    Start-Sleep -Seconds $PollSeconds
  }

  $trainingCodeText = (Get-Content -LiteralPath $TrainingExitFile -Raw).Trim()
  Write-WatchLog "training_exit_detected code=$trainingCodeText"
  if ($trainingCodeText -ne "0") {
    Write-WatchLog "training did not complete successfully; postprocess skipped"
    Set-Content -LiteralPath $watchExit -Value 10
    exit 10
  }

  $env:WSLENV = "OPENAI_API_KEY/u"
  $postprocessLog = Join-Path $logDir "watch_triggered_stage1_postprocess_${CandidateKey}_$stamp.log"
  Write-WatchLog "postprocess_started log=$postprocessLog"
  wsl.exe bash -lc "source ~/miniconda3/etc/profile.d/conda.sh && conda activate clearread-llama-lora && cd /mnt/c/Users/Aufb/Desktop/fit5120/iteration3/new-model/fine_tune_sweep && bash scripts/postprocess_stage1_candidate.sh $CandidateKey $JudgeRunId" > $postprocessLog 2>&1
  $postCode = $LASTEXITCODE
  Write-WatchLog "postprocess_finished code=$postCode"
  Set-Content -LiteralPath $watchExit -Value $postCode
  exit $postCode
} catch {
  Write-WatchLog "watch_failed $($_.Exception.GetType().FullName): $($_.Exception.Message)"
  Set-Content -LiteralPath $watchExit -Value 1
  exit 1
}
