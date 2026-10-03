param([switch]$SkipInstall, [switch]$SkipFrontend)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Executable $Arguments" }
}

$Node = (Get-Command node.exe -ErrorAction Stop).Source
$Uv = (Get-Command uv.exe -ErrorAction Stop).Source
$Npm = (Get-Command npm.cmd -ErrorAction Stop).Source
$NodeVersion = [version]((& $Node --version).TrimStart('v'))
if ($NodeVersion -lt [version]'22.19.0') { throw 'Node.js 22.19+ is required.' }
if ((& $Node -p 'process.arch') -ne 'x64') { throw 'Use an x64 Node.js runtime for this Windows x64 package.' }
$BuildRoot = Join-Path $RepoRoot 'build/windows'
New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null
$BuildPython = Join-Path $RepoRoot '.venv-build/Scripts/python.exe'
if (-not $SkipInstall) {
    if (-not (Test-Path -LiteralPath $BuildPython)) {
        Invoke-Checked $Uv @('venv', '--python', '3.12', '.venv-build')
    }
    Invoke-Checked $Uv @('export', '--frozen', '--project', 'backend', '--no-dev', '--no-emit-project', '--no-hashes', '--output-file', "$BuildRoot/runtime-requirements.txt")
    Invoke-Checked $Uv @('pip', 'install', '--python', $BuildPython, '-r', "$BuildRoot/runtime-requirements.txt", '-r', 'packaging/windows/requirements.txt')
    Push-Location frontend
    try { Invoke-Checked $Npm @('ci', '--no-audit', '--no-fund') } finally { Pop-Location }
}
Invoke-Checked $BuildPython @('-c', 'import struct, sys; assert struct.calcsize("P") == 8 and sys.version_info[:2] == (3, 12), "Python 3.12 x64 is required"')
if (-not $SkipFrontend) {
    $PreviousDesktopBuild = [Environment]::GetEnvironmentVariable('DISPROT_DESKTOP_BUILD')
    $PreviousTelemetry = [Environment]::GetEnvironmentVariable('NEXT_TELEMETRY_DISABLED')
    $env:DISPROT_DESKTOP_BUILD = '1'
    $env:NEXT_TELEMETRY_DISABLED = '1'
    Push-Location frontend
    try { Invoke-Checked $Npm @('run', 'build') }
    finally {
        Pop-Location
        [Environment]::SetEnvironmentVariable('DISPROT_DESKTOP_BUILD', $PreviousDesktopBuild)
        [Environment]::SetEnvironmentVariable('NEXT_TELEMETRY_DISABLED', $PreviousTelemetry)
    }
}
Invoke-Checked $BuildPython @('packaging/windows/stage.py', '--node', $Node)
Invoke-Checked $BuildPython @('-m', 'PyInstaller', '--noconfirm', '--clean', '--distpath', 'dist/windows', '--workpath', 'build/windows/pyinstaller', 'packaging/windows/disprot.spec')

$Compiler = Join-Path $RepoRoot '.tools/InnoSetup/ISCC.exe'
if (-not (Test-Path -LiteralPath $Compiler)) {
    $ToolRoot = Join-Path $RepoRoot '.tools'
    New-Item -ItemType Directory -Force -Path $ToolRoot | Out-Null
    $Download = Join-Path $ToolRoot 'innosetup-6.7.3.exe'
    if (-not (Test-Path -LiteralPath $Download)) {
        Invoke-WebRequest 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe' -OutFile $Download
    }
    $ExpectedHash = '9C73C3BAE7ED48D44112A0F48E66742C00090BDB5BEF71D9D3C056C66E97B732'
    if ((Get-FileHash -LiteralPath $Download -Algorithm SHA256).Hash -ne $ExpectedHash) {
        throw 'Inno Setup download checksum mismatch.'
    }
    if ((Get-AuthenticodeSignature -LiteralPath $Download).Status -ne 'Valid') {
        throw 'Inno Setup Authenticode signature is not valid.'
    }
    $ToolInstaller = Start-Process -FilePath $Download -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER', '/NOICONS', ('/DIR="' + $ToolRoot + '\InnoSetup"')) -WindowStyle Hidden -Wait -PassThru
    if ($ToolInstaller.ExitCode -ne 0) { throw "Inno Setup installation failed: $($ToolInstaller.ExitCode)" }
}
Invoke-Checked $Compiler @("/DRepoRoot=$RepoRoot", 'packaging/windows/installer.iss')
Copy-Item -LiteralPath 'packaging/windows/README.txt' -Destination 'dist/windows/README.txt'
$Hashes = Get-ChildItem -LiteralPath 'dist/windows' -Filter '*.exe' | Get-FileHash -Algorithm SHA256 | ForEach-Object {
    $_.Hash.ToLowerInvariant() + '  ' + (Split-Path -Leaf $_.Path)
}
$Hashes | Set-Content -LiteralPath 'dist/windows/SHA256SUMS.txt' -Encoding ascii
Get-ChildItem -LiteralPath 'dist/windows' -File | Select-Object Name, Length
