# start_fleet.ps1 - launch and supervise N parallel worker_direct.py processes.
#
# PARALLELISM MODEL
#   Generation (llama) runs concurrently across workers. The apply/build/verify
#   step is serialised by a cross-process lock, because all workers share ONE
#   repo and ONE build directory. Without that lock, worker A's edit would be
#   in the tree while worker B builds, and B could record a false match.
#
#   So N = generations in flight. Throughput is bounded by the build
#   (~40-70s each) once N exceeds a handful. 4 is a good default; 8 mostly
#   queues on the lock unless generation is much slower than the build.
#
#   llama-server must be started with slots or generation serialises anyway:
#       llama-server -c 60000 --parallel 4 --cont-batching ...
#   --parallel divides total context across slots (4 slots of 15k here), it
#   does not multiply VRAM.
#
# SHUTDOWN
#   Ctrl-C stops the fleet cleanly: child processes are killed and any records
#   they were holding are returned to 'todo'. Windows kills are hard (no
#   signal), so the worker cannot release its own claim; the launcher does it.
#
# Usage:
#   .\automation\win\start_fleet.ps1                      # 4 workers
#   .\automation\win\start_fleet.ps1 -Workers 8
#   .\automation\win\start_fleet.ps1 -Workers 4 -Max 20   # 20 functions each
#   .\automation\win\start_fleet.ps1 -DryRun              # no model calls

param(
    [int]$Workers = 4,
    [int]$Max = 0,
    [int]$StatusEvery = 20,     # seconds between status lines
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$repo    = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$worker  = Join-Path $PSScriptRoot "worker_direct.py"
$logDir  = Join-Path $repo "automation\logs"
$lock    = Join-Path $repo "automation\.build.lock"
$distro  = if ($env:SOTN_WSL_DISTRO) { $env:SOTN_WSL_DISTRO } else { "Ubuntu-24.04" }
# NOTE: do not use a scriptblock with -replace here. That is PowerShell 6+ only;
# Windows PowerShell 5.1 stringifies the block instead of invoking it, producing
# a path like "/mnt/ + C:/...Groups[1].Value.ToLower()". Plain string ops work on both.
$wslRepo = '/mnt/' + $repo.Substring(0,1).ToLower() + (($repo.Substring(2)) -replace '\\','/')

if (-not (Test-Path $worker)) { throw "worker not found: $worker" }
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Invoke-Sched([string]$SchedArgs) {
    # Run scheduler.py in WSL and return its output.
    & wsl.exe -d $distro -e bash -lc "cd '$wslRepo' && python3 automation/scheduler.py $SchedArgs" 2>&1
}

# --- preflight ---------------------------------------------------------------
if (Test-Path $lock) {
    $age = (Get-Date) - (Get-Item $lock).LastWriteTime
    if ($age.TotalSeconds -gt 3600) {
        Remove-Item $lock -Force
        Write-Host "[fleet] removed stale build lock ($([int]$age.TotalSeconds)s old)" -ForegroundColor Yellow
    } else {
        Write-Host "[fleet] build lock present ($([int]$age.TotalSeconds)s old); a worker may still be running" -ForegroundColor Yellow
    }
}

Write-Host "[fleet] reclaiming claims left by any previous run..." -ForegroundColor Cyan
Invoke-Sched "reclaim --older-than-min 0" | ForEach-Object { Write-Host "  $_" }

$startStats = Invoke-Sched "stats"
Write-Host "[fleet] queue before start:" -ForegroundColor Cyan
$startStats | ForEach-Object { Write-Host "  $_" }

# --- launch ------------------------------------------------------------------
$wArgs = @("loop")
if ($Max -gt 0) { $wArgs += @("--max", "$Max") }
if ($DryRun)    { $wArgs += "--dry-run" }

Write-Host "`n[fleet] starting $Workers worker(s); logs in $logDir" -ForegroundColor Cyan
$procs = @()
for ($i = 1; $i -le $Workers; $i++) {
    $log = Join-Path $logDir "worker-$i.log"
    Remove-Item $log,"$log.err" -Force -ErrorAction SilentlyContinue
    $env:WORKER_NAME = "fleet-$i"
    $p = Start-Process -FilePath "python" -ArgumentList (@($worker) + $wArgs) `
                       -RedirectStandardOutput $log -RedirectStandardError "$log.err" `
                       -NoNewWindow -PassThru
    $procs += [pscustomobject]@{ Id = $i; Proc = $p; Log = $log; Offset = [long]0 }
    Add-Content -Path (Join-Path $logDir "fleet.pids") -Value $p.Id
    Write-Host ("  worker {0}  pid {1}" -f $i, $p.Id)
    Start-Sleep -Milliseconds 400   # stagger so they do not all claim at once
}

Write-Host "`n[fleet] running. Ctrl-C stops all workers and releases their claims.`n" -ForegroundColor Green

# --- supervise ---------------------------------------------------------------
# Poll rather than Wait-Process, so Ctrl-C is caught here and status is visible.
try {
    while ($true) {
        $alive = @($procs | Where-Object { -not $_.Proc.HasExited })
        if ($alive.Count -eq 0) { Write-Host "[fleet] all workers finished."; break }

        $stats = (Invoke-Sched "stats") -join ' '
        $m = [regex]::Match($stats, 'todo:\s*(\d+).*?claimed:\s*(\d+).*?near:\s*(\d+).*?matched:\s*(\d+).*?escalated:\s*(\d+)')
        $summary = if ($m.Success) {
            "todo {0}  claimed {1}  matched {2}  escalated {3}" -f `
                $m.Groups[1].Value, $m.Groups[2].Value, $m.Groups[4].Value, $m.Groups[5].Value
        } else { "queue unavailable" }

        Write-Host ("[{0}] {1} worker(s) alive | {2}" -f (Get-Date -Format HH:mm:ss), $alive.Count, $summary) -ForegroundColor Cyan

        # Stream every new line each worker has written since the last poll, in
        # full. The previous version printed only the LAST line, truncated to 96
        # chars, which meant a worker reasoning for 20 minutes showed the same
        # clipped sentence over and over and told you nothing about whether it
        # was progressing or wedged. Never abridge worker output.
        foreach ($w in $procs) {
            if (-not (Test-Path $w.Log)) { continue }
            $len = (Get-Item $w.Log).Length
            if ($len -gt $w.Offset) {
                $fs = [System.IO.File]::Open($w.Log, 'Open', 'Read', 'ReadWrite')
                try {
                    $null = $fs.Seek($w.Offset, 'Begin')
                    $sr = New-Object System.IO.StreamReader($fs)
                    $new = $sr.ReadToEnd()
                } finally { $fs.Close() }
                $w.Offset = $len
                foreach ($line in ($new -split "`r?`n")) {
                    if ($line.Trim()) { Write-Host ("    w{0}| {1}" -f $w.Id, $line) -ForegroundColor DarkGray }
                }
            }
        }
        Start-Sleep -Seconds $StatusEvery
    }
}
finally {
    Write-Host "`n[fleet] shutting down..." -ForegroundColor Yellow
    foreach ($w in $procs) {
        if (-not $w.Proc.HasExited) {
            Write-Host "  stopping worker $($w.Id) (pid $($w.Proc.Id))"
            # taskkill /T kills the whole process TREE. Stop-Process only killed
            # the launcher, leaving the python worker orphaned and still running,
            # which is why Ctrl-C appeared to do nothing.
            try { & taskkill.exe /PID $w.Proc.Id /T /F 2>&1 | Out-Null } catch {}
            try { Stop-Process -Id $w.Proc.Id -Force -ErrorAction SilentlyContinue } catch {}
        }
    }
    Start-Sleep -Seconds 1

    # Hard-killed workers cannot release their own claims, so do it here.
    Write-Host "[fleet] releasing claims held by stopped workers..." -ForegroundColor Yellow
    Invoke-Sched "reclaim --older-than-min 0" | ForEach-Object { Write-Host "  $_" }

    if (Test-Path $lock) {
        Remove-Item $lock -Force -ErrorAction SilentlyContinue
        Write-Host "  cleared build lock"
    }

    Write-Host "[fleet] final queue state:" -ForegroundColor Cyan
    Invoke-Sched "stats" | ForEach-Object { Write-Host "  $_" }
    Write-Host "[fleet] logs: $logDir" -ForegroundColor DarkGray
}
