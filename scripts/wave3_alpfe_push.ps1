# Wave 3 — alpfe-push experiments for the v2.2 closeout 6/6 attempt.
#
# Based on the 22-experiment overnight summary, alpfe was structurally
# stuck at 0.80–0.94 off Carroll EXCEPT for nb27_v2_3_raw_fet_eqpac_w0.01
# (alpfe 0.392 — within cal-grade band) which broke scav_rat to 2.556.
# That's the classic alpfe-scav_rat identifiability degeneracy under
# z-scored loss.
#
# Hypothesis: combining the alpfe-pushing raw_fet term with the
# scav_rat-holding PINN drift term should let both recover simultaneously.
#
# Three experiments queued, sequential (no multi-process CUDA on Windows —
# memory: feedback_no_parallel_cuda_on_windows.md):
#
#   1. raw_fet w=0.005 + PINN drift w=3.0  — gentler raw_fet, may preserve
#      Biggrow/diatomgraz/R_PICPOC while moving alpfe.
#   2. raw_fet w=0.01  + PINN drift w=3.0  — replicate the alpfe-rescuing
#      raw_fet weight with PINN drift holding the iron mass balance.
#   3. PINN drift w=5.0 alone              — sweep extension; tests if
#      higher drift weight alone can move alpfe (previous w=0.05/0.3/1.0/3.0
#      showed alpfe nearly flat).
#
# Wall-clock ~4.5h on RTX 5090 Laptop (~90 min per experiment).
#
# Usage (from repo root):
#   ./scripts/wave3_alpfe_push.ps1

$ErrorActionPreference = "Continue"
$LogPath = Join-Path $PSScriptRoot "wave3_alpfe_push_log.txt"

$experiments = @(
    # 1. raw_fet w=0.005 + PINN drift w=3.0 (combo, gentler raw_fet)
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.005"; pinn_weight = "3.0"; pinn_type = "drift" },
    # 2. raw_fet w=0.01 + PINN drift w=3.0 (combo, alpfe-rescuing raw_fet)
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.01";  pinn_weight = "3.0"; pinn_type = "drift" },
    # 3. PINN drift w=5.0 alone (sweep extension)
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.0";   pinn_weight = "5.0"; pinn_type = "drift" }
)

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Message"
    Write-Output $line
    Add-Content -Path $LogPath -Value $line
}

Write-Log "=== Wave 3 alpfe-push start, $($experiments.Count) experiments queued ==="
Write-Log "GPU baseline: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null)"

$completed = 0
$failed = 0

foreach ($exp in $experiments) {
    $env:NB23_SEED = $exp.nb_seed
    $env:NB23_FET_WEIGHT = $exp.fet_weight
    $env:NB23_RAW_FET_WEIGHT = $exp.raw_fet_weight
    $env:NB23_PINN_WEIGHT = $exp.pinn_weight
    $env:NB23_PINN_TYPE = $exp.pinn_type
    $env:NB23_LUMPED_MAPPING = "0"
    $tag = "seed=$($exp.nb_seed) fet_w=$($exp.fet_weight) raw_fet_w=$($exp.raw_fet_weight) pinn_w=$($exp.pinn_weight) pinn_t=$($exp.pinn_type)"

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

Write-Log "=== Wave 3 alpfe-push done. $completed succeeded, $failed failed ==="

Write-Log "Aggregating results into v2.2_overnight_summary..."
$summaryOutput = & python scripts/overnight_summary.py 2>&1
Write-Log $summaryOutput

Remove-Item Env:NB23_SEED -ErrorAction SilentlyContinue
Remove-Item Env:NB23_FET_WEIGHT -ErrorAction SilentlyContinue
Remove-Item Env:NB23_RAW_FET_WEIGHT -ErrorAction SilentlyContinue
Remove-Item Env:NB23_PINN_WEIGHT -ErrorAction SilentlyContinue
Remove-Item Env:NB23_PINN_TYPE -ErrorAction SilentlyContinue
Remove-Item Env:NB23_LUMPED_MAPPING -ErrorAction SilentlyContinue

Write-Log "Done. Sort by alpfe column ASC in v2.2_overnight_summary.{md,csv} to see if combos broke the alpfe-scav_rat tradeoff."
