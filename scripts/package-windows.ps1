param(
    [string]$Iscc = 'ISCC.exe',
    [string]$CertificateThumbprint,
    [string]$TimestampUrl,
    [string]$SignTool = 'signtool.exe'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$signed = $PSBoundParameters.ContainsKey('CertificateThumbprint')
if ($signed) {
    if ($env:GOREECLOUD_RELEASE_ENABLED -cne 'yes') { throw 'Signed Windows releases require GOREECLOUD_RELEASE_ENABLED=yes' }
    if ([string]::IsNullOrWhiteSpace($env:GOREECLOUD_WINDOWS_CERT_SUBJECT)) {
        throw 'Set GOREECLOUD_WINDOWS_CERT_SUBJECT to the exact subject of your code-signing certificate'
    }
    if ($CertificateThumbprint -notmatch '^[0-9a-fA-F]{40}$') { throw 'Provide the 40-character signing certificate thumbprint' }
    if (!(Test-Path "Cert:\CurrentUser\My\$CertificateThumbprint")) { throw 'Signing certificate not found in CurrentUser\My; connect your token or cloud signing client first' }
    $certificate = Get-Item "Cert:\CurrentUser\My\$CertificateThumbprint"
    if ($certificate.Subject -cne $env:GOREECLOUD_WINDOWS_CERT_SUBJECT) {
        throw 'Certificate subject differs from GOREECLOUD_WINDOWS_CERT_SUBJECT; refusing to sign with the wrong publisher'
    }
    $now = Get-Date
    if (!$certificate.HasPrivateKey -or $certificate.NotBefore -gt $now -or $certificate.NotAfter -le $now -or
        '1.3.6.1.5.5.7.3.3' -notin $certificate.EnhancedKeyUsageList.ObjectId.Value) {
        throw 'A valid code-signing certificate with access to its private key is required'
    }
    $timestamp = [uri]$TimestampUrl
    if (!$timestamp.IsAbsoluteUri -or $timestamp.Scheme -notin @('http', 'https') -or $TimestampUrl -match '[\s"$]') {
        throw 'Provide an absolute HTTP(S) RFC 3161 timestamp URL without spaces, quotes or dollar signs'
    }
    $SignTool = (Get-Command $SignTool -CommandType Application).Source
}
$mode = if ($signed) { 'signed' } else { 'unsigned' }
$output = Join-Path $root "dist/windows/$mode"
$stage = Join-Path $output ([guid]::NewGuid().ToString('N'))
Push-Location $root
try {
    & cargo build --release --locked
    if ($LASTEXITCODE -ne 0) { throw 'Windows build failed' }
    $version = (Select-String -Path Cargo.toml -Pattern '^version = "([^"]+)"' | Select-Object -First 1).Matches[0].Groups[1].Value
    New-Item -ItemType Directory -Force $stage | Out-Null
    Copy-Item target/release/goreecloud_rich_text_editor.exe $stage -Force
    if (!$env:VCToolsRedistDir) { throw 'Run from a Visual Studio developer shell to locate the C++ runtime' }
    $runtime = Get-ChildItem (Join-Path $env:VCToolsRedistDir 'x64/Microsoft.VC*.CRT/vcruntime140.dll') | Select-Object -First 1
    if (!$runtime) { throw 'The redistributable x64 vcruntime140.dll was not found' }
    Copy-Item $runtime.FullName $stage -Force
    $compilerArgs = @("/DAppVersion=$version", "/DAppSource=$stage", "/O$stage")
    if ($signed) {
        $signScript = Join-Path $PSScriptRoot 'sign-windows-file.ps1'
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $signScript -FilePath "$stage/goreecloud_rich_text_editor.exe" -CertificateThumbprint $CertificateThumbprint -TimestampUrl $TimestampUrl -SignTool $SignTool
        if ($LASTEXITCODE -ne 0) { throw 'Application signing failed' }
        # Inno expands $q/$f itself; escape literal dollar signs in local paths.
        $ps = (Get-Command powershell.exe -CommandType Application).Source.Replace('$', '$$')
        $scriptPath = $signScript.Replace('$', '$$')
        $toolPath = $SignTool.Replace('$', '$$')
        $signCommand = '$q{0}$q -NoProfile -ExecutionPolicy Bypass -File $q{1}$q -CertificateThumbprint {2} -TimestampUrl $q{3}$q -SignTool $q{4}$q -FilePath $f' -f $ps, $scriptPath, $CertificateThumbprint, $TimestampUrl, $toolPath
        $compilerArgs += @('/DSigned', "/Sgoreecloudrte=$signCommand")
    }
    & $Iscc @compilerArgs packaging/windows/goreecloud-rich-text-editor.iss
    if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
    $name = "goreecloud-rich-text-editor-$version-windows-x64-setup.exe"
    $installer = Join-Path $stage $name
    if ($signed) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $signScript -VerifyOnly -FilePath $installer -CertificateThumbprint $CertificateThumbprint -TimestampUrl $TimestampUrl -SignTool $SignTool
        if ($LASTEXITCODE -ne 0) { throw 'Installer signature verification failed' }
    }
    $hash = (Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant()
    [System.IO.File]::WriteAllText("$installer.sha256", "$hash  $name`n", [System.Text.Encoding]::ASCII)
    Copy-Item $installer, "$installer.sha256" $output -Force
    Write-Output "$mode installer: $(Join-Path $output $name)"
} finally { Pop-Location }
