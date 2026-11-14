# Windows x64 installer lifecycle QA. ONLY run in GitHub Actions or an explicitly
# authorized disposable Windows VM/account; it writes per-user file associations.
# Does not start the GUI and never opens the user's regular notes library.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Installer
)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -and $env:GOREECLOUD_WINDOWS_SMOKE_TEST -ne 'yes') {
    throw 'Windows installer smoke testing requires GITHUB_ACTIONS=true or GOREECLOUD_WINDOWS_SMOKE_TEST=yes on a disposable account'
}
if ($env:OS -ne 'Windows_NT') { throw 'This smoke test requires Windows' }
$installerFile = (Resolve-Path -LiteralPath $Installer).Path
if ([IO.Path]::GetFileName($installerFile) -notmatch '^goreecloud-rich-text-editor-\d+\.\d+\.\d+-windows-x64-setup\.exe$') {
    throw 'Unrecognized GoreeCloud Windows installer name'
}

function Invoke-Inno([string]$binary, [string[]]$arguments, [string]$label) {
    $proc = Start-Process -FilePath $binary -ArgumentList $arguments -PassThru
    try {
        if (-not $proc.WaitForExit(120000)) {
            $proc.Kill()
            throw "$label timed out after 120 seconds"
        }
        if ($proc.ExitCode -ne 0) { throw "$label exited with code $($proc.ExitCode)" }
    } finally {
        $proc.Dispose()
    }
}

$root = Join-Path ([IO.Path]::GetTempPath()) ('goreecloud-installer-smoke-' + [guid]::NewGuid().ToString('N'))
$appDir = Join-Path $root 'App Under Test'
$notes = Join-Path $root 'External Notes with spaces'
$note = Join-Path $notes 'Unicode 文档.md'
$uninstaller = Join-Path $appDir 'unins000.exe'
$progid = 'Registry::HKEY_CURRENT_USER\Software\Classes\GoreeCloudRte.Markdown'
$complete = $false

New-Item -ItemType Directory -Path $notes -Force | Out-Null
[IO.File]::WriteAllText($note, ('# Local-first smoke test' + [Environment]::NewLine + 'Markdown 文件 preserved after uninstall' + [Environment]::NewLine), [Text.Encoding]::UTF8)
$expected = (Get-FileHash -LiteralPath $note -Algorithm SHA256).Hash
try {
    $installArgs = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NOICONS',
        ('/DIR="' + $appDir + '"'), ('/LOG="' + (Join-Path $root 'install.log') + '"'))
    Invoke-Inno $installerFile $installArgs 'Install'
    foreach ($file in @('goreecloud_rich_text_editor.exe', 'vcruntime140.dll', 'LICENSE', 'THIRD_PARTY.md', 'unins000.exe')) {
        if (-not (Test-Path -LiteralPath (Join-Path $appDir $file) -PathType Leaf)) {
            throw "Installer did not include required $file"
        }
    }
    if (-not (Test-Path -LiteralPath $progid)) {
        throw 'Per-user Markdown Open With registry association is missing'
    }
    Write-Output 'Fresh silent installation and Markdown association passed'

    # Reinstall tests the upgrade path and must not change independent notes.
    $again = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NOICONS',
        ('/DIR="' + $appDir + '"'), ('/LOG="' + (Join-Path $root 'reinstall.log') + '"'))
    Invoke-Inno $installerFile $again 'Reinstall'
    if (-not (Test-Path -LiteralPath (Join-Path $appDir 'goreecloud_rich_text_editor.exe'))) {
        throw 'Application missing after reinstall'
    }
    if ((Get-FileHash -LiteralPath $note -Algorithm SHA256).Hash -ne $expected) {
        throw 'Independent notes changed during installation/reinstallation'
    }
    Write-Output 'Reinstall preserved independent Markdown note'

    $removeArgs = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
        ('/LOG="' + (Join-Path $root 'uninstall.log') + '"'))
    Invoke-Inno $uninstaller $removeArgs 'Uninstall'
    Start-Sleep -Milliseconds 500
    if (Test-Path -LiteralPath (Join-Path $appDir 'goreecloud_rich_text_editor.exe')) {
        throw 'Application still installed after silent uninstall'
    }
    if (Test-Path -LiteralPath $progid) {
        throw 'Markdown Open With registry key survived uninstall'
    }
    if ((Get-FileHash -LiteralPath $note -Algorithm SHA256).Hash -ne $expected) {
        throw 'Independent Markdown note changed during uninstall'
    }
    Write-Output 'Uninstall removed app and file association but preserved external notes'
    $complete = $true
}
finally {
    if ($complete) {
        Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        Write-Warning "Installer smoke failed. Disposable QA files and logs left for inspection at $root"
        if (Test-Path -LiteralPath $uninstaller) {
            try {
                Invoke-Inno $uninstaller @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') 'Best-effort uninstall after failed smoke'
            } catch { Write-Warning "Best-effort uninstall failed: $_" }
        }
    }
}
if (-not $complete) { throw 'Windows installer lifecycle smoke incomplete' }
Write-Output 'WINDOWS_INSTALL_REINSTALL_UNINSTALL_SMOKE_PASS'
