param(
    [Parameter(Mandatory = $true)]
    [string]$VmSshTarget,

    [string]$SourceAdapterDir = "C:\Users\Aufb\Desktop\fit5120\iteration3\new-model\fine_tune_sweep\phase2_48h_search\model_workspaces\llama32_3b_instruct\models\adapters\phase2_r32_a64_lr1p5e4_epoch_4",

    [string]$RemoteRoot = "/opt/clearread-ai-summary/models/adapters"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourceAdapterDir)) {
    throw "Adapter directory does not exist: $SourceAdapterDir"
}

$adapterName = Split-Path -Leaf $SourceAdapterDir
$remotePath = "$RemoteRoot/$adapterName"

ssh $VmSshTarget "mkdir -p '$remotePath'"
scp -r "$SourceAdapterDir\*" "${VmSshTarget}:$remotePath/"

Write-Host "Uploaded adapter to ${VmSshTarget}:$remotePath"
Write-Host "Run verify_adapter_hashes.ps1 or sha256sum on the VM before starting production."
