param(
    [string]$AdapterDir = "C:\Users\Aufb\Desktop\fit5120\iteration3\new-model\fine_tune_sweep\phase2_48h_search\model_workspaces\llama32_3b_instruct\models\adapters\phase2_r32_a64_lr1p5e4_epoch_4"
)

$ErrorActionPreference = "Stop"

$expected = @{
    "adapter_config.json" = "21DA9309A6CD6427820C6E9A9644DF5FBB17C1A9565C0E04AB9339463A03F913"
    "adapter_model.safetensors" = "02855217765B31D563F73DEDEA8828636B5A4973F0D0B41609594CEBC1564926"
    "chat_template.jinja" = "5816FCE10444E03C2E9EE1EF8A4A1EA61AE7E69E438613F3B17B69D0426223A4"
    "tokenizer.json" = "6B9E4E7FB171F92FD137B777CC2714BF87D11576700A1DCD7A399E7BBE39537B"
    "tokenizer_config.json" = "3C8420428C795BE2203153F82DA96A3348FEEA02E5AF02113CF7E7936A739BB8"
    "snapshot_manifest.json" = "6D39355741D1EAF3AECA861230860BD3745509D2BB5AC9120B0CA936F673A4A0"
}

foreach ($name in $expected.Keys) {
    $path = Join-Path $AdapterDir $name
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing adapter file: $name"
    }
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash
    if ($hash -ne $expected[$name]) {
        throw "Hash mismatch for ${name}: expected $($expected[$name]) got $hash"
    }
    Write-Host "OK $name $hash"
}

Write-Host "All adapter hashes match."
