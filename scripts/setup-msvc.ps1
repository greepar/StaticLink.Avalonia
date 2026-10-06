param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('x64', 'amd64', 'x86', 'amd64_arm64', 'arm64')]
    [string]$Architecture
)
$ErrorActionPreference = 'Stop'
$target = switch ($Architecture) {
    'x64' { 'amd64' }
    'amd64_arm64' { 'arm64' }
    default { $Architecture }
}
$before = @{}
Get-ChildItem Env: | ForEach-Object { $before[$_.Name] = $_.Value }
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$hostArchitecture = if ([Runtime.InteropServices.RuntimeInformation]::OSArchitecture -eq 'Arm64') { 'arm64' } else { 'amd64' }
# Native ARM images can install a versioned C++ component ID. Validate
# the actual compiler after entering the developer shell instead.
$installation = & $vswhere -latest -products '*' -version '[17.0,18.0)' -property installationPath
if ($LASTEXITCODE -ne 0 -or -not $installation) { throw 'Visual Studio 2022 C++ tools were not found.' }
$launcher = Join-Path $installation 'Common7/Tools/Launch-VsDevShell.ps1'
& $launcher -Arch $target -HostArch $hostArchitecture -SkipAutomaticLocation
if (-not (Get-Command cl.exe -ErrorAction SilentlyContinue)) { throw 'MSVC environment did not expose cl.exe.' }
if ($env:GITHUB_ENV) {
    Get-ChildItem Env: | Where-Object {
        $_.Name -notmatch '^(GITHUB_|RUNNER_|NODE_OPTIONS$)' -and $before[$_.Name] -cne $_.Value
    } | ForEach-Object {
        $delimiter = 'MSVC_' + [Guid]::NewGuid().ToString('N')
        "$($_.Name)<<$delimiter`n$($_.Value)`n$delimiter" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
    }
}
Write-Host "MSVC target: $env:VSCMD_ARG_TGT_ARCH; host: $env:VSCMD_ARG_HOST_ARCH"
