@echo off
REM ---------------------------------------------------------------------------
REM sotn.cmd - Windows entry point for the SOTN build, forwarded into WSL.
REM
REM Topology A: OpenCode and llama-server run natively on Windows; only the
REM build toolchain and the repo live in WSL. This wrapper lets Windows callers
REM (you, or an OpenCode worker) run build/diff/permuter/git commands against
REM the WSL toolchain without hand-writing wsl.exe invocations.
REM
REM Usage:   sotn build [version]
REM          sotn diff <symbol> [version] [overlay]
REM          sotn commit "message"
REM          sotn help
REM
REM Env:  SOTN_WSL_DISTRO  (default Ubuntu-24.04)
REM       SOTN_WSL_REPO    absolute WSL path to the repo; auto-detected as
REM                        $HOME/sotn-decomp when unset
REM
REM Install: add this folder to PATH, or call it by full path.
REM
REM Note: bash is invoked with the script path and arguments as separate argv
REM entries (not a -lc string), so Windows quoting is translated by wsl.exe
REM rather than being re-parsed by a shell. That keeps quoted commit messages
REM intact.
REM ---------------------------------------------------------------------------
setlocal

if not defined SOTN_WSL_DISTRO set "SOTN_WSL_DISTRO=Ubuntu-24.04"

REM Single-tree layout: the repo lives in the Windows project directory. WSL
REM reaches that same directory through /mnt/c, so there is nothing to sync.
REM SOTN_WSL_REPO is that path as WSL sees it.
REM Derived from THIS script's own location, never hardcoded: an absolute home
REM path would leak a username into a public repo and break on any other machine.
REM %~dp0 is <repo>\automation\win\ ; two levels up is the repo root. Then
REM C:\foo -> /mnt/c/foo.
if not defined SOTN_WSL_REPO (
  pushd "%~dp0..\.."
  set "_SOTN_WIN_ROOT=%CD%"
  popd
  REM wslpath is WSL's own converter. Doing this by hand in cmd means
  REM lowercasing the drive letter, which batch cannot do cleanly.
  for /f "usebackq delims=" %%P in (
    `wsl.exe -d %SOTN_WSL_DISTRO% -e wslpath -a "%_SOTN_WIN_ROOT%"`
  ) do set "SOTN_WSL_REPO=%%P"
)

wsl.exe -d %SOTN_WSL_DISTRO% -e bash "%SOTN_WSL_REPO%/automation/win/sotn_dispatch.sh" %*
exit /b %ERRORLEVEL%
