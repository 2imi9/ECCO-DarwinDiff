# DarwinDiff overnight experiment runner.
#
# Sequential nbconvert execution of an experiment queue defined below.
# Robust to individual failures (try/catch per experiment, continues queue).
# Logs everything to scripts/overnight_log.txt with timestamps.
# Aggregates results into docs/findings/v2.2_overnight_summary.md at end.
#
# Usage (from repo root):
#   ./scripts/overnight_run.ps1
#
# Designed for the Windows + single-GPU + no-multi-process-CUDA constraints
# documented in auto-memory `feedback_no_parallel_cuda_on_windows.md`.

$ErrorActionPreference = "Continue"
$LogPath = Join-Path $PSScriptRoot "overnight_log.txt"

# Experiment queue. Each entry produces one executed notebook.
# Format: ordered hashtable per experiment.
#   nb_seed:           NB23_SEED env var
#   fet_weight:        NB23_FET_WEIGHT (z-scored FeT loss multiplier)
#   raw_fet_weight:    NB23_RAW_FET_WEIGHT (raw-magnitude FeT term weight)
$experiments = @(
    # v2.3 raw-FeT weight sweep (extending tonight's w=0.1/0.3/0.05)
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.01"; pinn_weight = "0.0"; pinn_type = "balance" },
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.5";  pinn_weight = "0.0"; pinn_type = "balance" },
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "3.0";  pinn_weight = "0.0"; pinn_type = "balance" },

    # v2.4 PINN iron mass-balance (strict source = sink) - primary test
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.0"; pinn_weight = "0.3"; pinn_type = "balance" },
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.0"; pinn_weight = "1.0"; pinn_type = "balance" },

    # v2.4 PINN drift variant (penalize relative rate of change) - more
    # defensible since it doesn't require strict 50-day steady state
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.0"; pinn_weight = "0.3"; pinn_type = "drift" },
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.0"; pinn_weight = "1.0"; pinn_type = "drift" },

    # nb23 multi-seed robustness (baseline, no FeT/PINN modifications)
    @{ nb_seed = "1"; fet_weight = "1.0"; raw_fet_weight = "0.0"; pinn_weight = "0.0"; pinn_type = "balance" },
    @{ nb_seed = "2"; fet_weight = "1.0"; raw_fet_weight = "0.0"; pinn_weight = "0.0"; pinn_type = "balance" },
    @{ nb_seed = "3"; fet_weight = "1.0"; raw_fet_weight = "0.0"; pinn_weight = "0.0"; pinn_type = "balance" },
    @{ nb_seed = "4"; fet_weight = "1.0"; raw_fet_weight = "0.0"; pinn_weight = "0.0"; pinn_type = "balance" }
)

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Message"
    Write-Output $line
    Add-Content -Path $LogPath -Value $line
}

Write-Log "=== Overnight run start, $($experiments.Count) experiments queued ==="
Write-Log "GPU baseline: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null)"

$completed = 0
$failed = 0

foreach ($exp in $experiments) {
    $env:NB23_SEED = $exp.nb_seed
    $env:NB23_FET_WEIGHT = $exp.fet_weight
    $env:NB23_RAW_FET_WEIGHT = $exp.raw_fet_weight
    $env:NB23_PINN_WEIGHT = $exp.pinn_weight
    $env:NB23_PINN_TYPE = $exp.pinn_type
    $tag = "seed=$($exp.nb_seed) fet_w=$($exp.fet_weight) raw_fet_w=$($exp.raw_fet_weight) pinn_w=$($exp.pinn_weight) pinn_t=$($exp.pinn_type)"

    Write-Log "BUILDING: $tag"
    $buildOutput = & python scripts/build_nb23.py 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "BUILD FAILED: $tag - skipping execute"
        Write-Log $buildOutput
        $failed++
        continue
    }
    # Extract notebook path from build output (last "Wrote: <path>" line)
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

Write-Log "=== Overnight run done. $completed succeeded, $failed failed ==="

# Aggregate results into a summary table
Write-Log "Aggregating results..."
$summaryOutput = & python scripts/overnight_summary.py 2>&1
Write-Log $summaryOutput

Write-Log "Summary written to docs/findings/v2.2_overnight_summary.md"
Write-Log "Done."

# Clean up env vars
Remove-Item Env:NB23_SEED -ErrorAction SilentlyContinue
Remove-Item Env:NB23_FET_WEIGHT -ErrorAction SilentlyContinue
Remove-Item Env:NB23_RAW_FET_WEIGHT -ErrorAction SilentlyContinue
Remove-Item Env:NB23_PINN_WEIGHT -ErrorAction SilentlyContinue
Remove-Item Env:NB23_PINN_TYPE -ErrorAction SilentlyContinue
