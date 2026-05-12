# DarwinDiff overnight Wave 2: re-run the 8 PINN experiments that crashed
# in Wave 1 due to the NameError bug (fixed in HEAD).
#
# Same robust pattern as overnight_run.ps1 but with the PINN-only subset.

$ErrorActionPreference = "Continue"
$LogPath = Join-Path $PSScriptRoot "overnight_log.txt"

$experiments = @(
    # v2.4 PINN balance
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.0"; pinn_weight = "0.3"; pinn_type = "balance" },
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.0"; pinn_weight = "1.0"; pinn_type = "balance" },

    # v2.4 PINN drift
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.0"; pinn_weight = "0.3"; pinn_type = "drift" },
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.0"; pinn_weight = "1.0"; pinn_type = "drift" },
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.0"; pinn_weight = "0.05"; pinn_type = "drift" },
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.0"; pinn_weight = "3.0";  pinn_type = "drift" },

    # v2.5 combo: raw_fet + PINN drift
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.05"; pinn_weight = "0.3"; pinn_type = "drift" },
    @{ nb_seed = "0"; fet_weight = "1.0"; raw_fet_weight = "0.05"; pinn_weight = "1.0"; pinn_type = "drift" }
)

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogPath -Value "[$ts] $Message"
}

Write-Log "=== Wave 2 start: 8 PINN experiments after bug fix ==="

$completed = 0; $failed = 0
foreach ($exp in $experiments) {
    $env:NB23_SEED = $exp.nb_seed
    $env:NB23_FET_WEIGHT = $exp.fet_weight
    $env:NB23_RAW_FET_WEIGHT = $exp.raw_fet_weight
    $env:NB23_PINN_WEIGHT = $exp.pinn_weight
    $env:NB23_PINN_TYPE = $exp.pinn_type
    $tag = "seed=$($exp.nb_seed) raw_fet_w=$($exp.raw_fet_weight) pinn_w=$($exp.pinn_weight) pinn_t=$($exp.pinn_type)"

    Write-Log "BUILDING: $tag"
    $buildOutput = & python scripts/build_nb23.py 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "BUILD FAILED: $tag"
        $failed++; continue
    }
    $nbPath = ($buildOutput | Select-String "^Wrote: (.+)$").Matches.Groups[1].Value
    Write-Log "EXECUTING: $nbPath"
    $start = Get-Date
    try {
        & jupyter nbconvert --to notebook --execute $nbPath --inplace --ExecutePreprocessor.timeout=7200 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Log "EXECUTE FAILED ($LASTEXITCODE): $nbPath"
            $failed++; continue
        }
        $elapsed = [int]((Get-Date) - $start).TotalMinutes
        Write-Log "OK ($elapsed min): $nbPath"
        $completed++
    } catch {
        Write-Log "EXCEPTION: $($_.Exception.Message)"
        $failed++
    }
}

Write-Log "=== Wave 2 done. $completed succeeded, $failed failed ==="
Write-Log "Re-aggregating with all results..."
& python scripts/overnight_summary.py 2>&1 | ForEach-Object { Write-Log $_ }
Write-Log "Done."

Remove-Item Env:NB23_SEED, Env:NB23_FET_WEIGHT, Env:NB23_RAW_FET_WEIGHT, Env:NB23_PINN_WEIGHT, Env:NB23_PINN_TYPE -ErrorAction SilentlyContinue
