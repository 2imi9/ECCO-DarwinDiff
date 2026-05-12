# Multi-seed robustness runner for v2.4 PINN drift w=3.0 — the 4/6 cal-grade
# winner from the v2.2 closeout. Verifies the result is not seed-lucky.
#
# Seed 0 already on disk (the published winner at
# notebooks/29_v2_4_pinn_drift_eqpac_w3.0.ipynb); this runner produces seeds
# 1..4 at notebooks/29_v2_4_pinn_drift_eqpac_w3.0_seed{1..4}.ipynb. Requires
# the build_nb23.py seed_suffix fix (commit 5795e4f) so each seed lands in
# its own file rather than clobbering the winner.
#
# Sequential only — no multi-process CUDA on Windows (memory:
# feedback_no_parallel_cuda_on_windows.md). Wall-clock ~6h on RTX 5090
# Laptop given the v2.4 PINN drift w=3.0 baseline runtime.
#
# Usage (from repo root):
#   ./scripts/multiseed_v2_4_drift_w3.ps1

$ErrorActionPreference = "Continue"
$LogPath = Join-Path $PSScriptRoot "multiseed_drift_w3_log.txt"

$experiments = @(
    @{ nb_seed = "1"; pinn_weight = "3.0"; pinn_type = "drift" },
    @{ nb_seed = "2"; pinn_weight = "3.0"; pinn_type = "drift" },
    @{ nb_seed = "3"; pinn_weight = "3.0"; pinn_type = "drift" },
    @{ nb_seed = "4"; pinn_weight = "3.0"; pinn_type = "drift" }
)

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Message"
    Write-Output $line
    Add-Content -Path $LogPath -Value $line
}

Write-Log "=== Multi-seed v2.4 PINN drift w=3.0 start, $($experiments.Count) seeds queued ==="
Write-Log "GPU baseline: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null)"

$completed = 0
$failed = 0

foreach ($exp in $experiments) {
    $env:NB23_SEED = $exp.nb_seed
    $env:NB23_FET_WEIGHT = "1.0"
    $env:NB23_RAW_FET_WEIGHT = "0.0"
    $env:NB23_PINN_WEIGHT = $exp.pinn_weight
    $env:NB23_PINN_TYPE = $exp.pinn_type
    $env:NB23_LUMPED_MAPPING = "0"
    $tag = "seed=$($exp.nb_seed) pinn_w=$($exp.pinn_weight) pinn_t=$($exp.pinn_type)"

    Write-Log "BUILDING: $tag"
    $buildOutput = & python scripts/build_nb23.py 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "BUILD FAILED: $tag"
        Write-Log $buildOutput
        $failed++
        continue
    }
    $nbPath = ($buildOutput | Select-String "^Wrote: (.+)$").Matches.Groups[1].Value
    if (-not $nbPath) {
        Write-Log "BUILD UNCLEAR (no Wrote: line): $tag"
        $failed++
        continue
    }
    Write-Log "EXECUTING: $nbPath"
    $execStart = Get-Date
    try {
        & jupyter nbconvert --to notebook --execute $nbPath --inplace --ExecutePreprocessor.timeout=7200 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Log "EXECUTE FAILED ($LASTEXITCODE): $nbPath"
            $failed++
            continue
        }
        $elapsed = [int]((Get-Date) - $execStart).TotalMinutes
        Write-Log "OK ($elapsed min): $nbPath"
        $completed++
    }
    catch {
        Write-Log "EXECUTE EXCEPTION: $($_.Exception.Message)"
        $failed++
    }
}

Write-Log "=== Multi-seed run done. $completed succeeded, $failed failed ==="

Write-Log "Aggregating results into v2.2_overnight_summary..."
$summaryOutput = & python scripts/overnight_summary.py 2>&1
Write-Log $summaryOutput

Remove-Item Env:NB23_SEED -ErrorAction SilentlyContinue
Remove-Item Env:NB23_FET_WEIGHT -ErrorAction SilentlyContinue
Remove-Item Env:NB23_RAW_FET_WEIGHT -ErrorAction SilentlyContinue
Remove-Item Env:NB23_PINN_WEIGHT -ErrorAction SilentlyContinue
Remove-Item Env:NB23_PINN_TYPE -ErrorAction SilentlyContinue
Remove-Item Env:NB23_LUMPED_MAPPING -ErrorAction SilentlyContinue

Write-Log "Done. Compare seeds 0-4 of nb29_v2_4_pinn_drift_eqpac_w3.0 in v2.2_overnight_summary.{md,csv}"
