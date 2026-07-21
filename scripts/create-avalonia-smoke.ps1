param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectDir,

    [Parameter(Mandatory = $true)]
    [string]$NuGetSource,

    [string]$StaticLinkVersion = "",

    [string]$AvaloniaVersion = "11.3.14",

    [string]$StaticLinkNativeVersion = ""
)

$ErrorActionPreference = "Stop"

$templateDir = Join-Path (Split-Path -Parent $PSScriptRoot) "Smoke/AvaloniaStaticLinkSmoke"
if (-not (Test-Path (Join-Path $templateDir "AvaloniaStaticLinkSmoke.csproj"))) {
    throw "Smoke project template was not found: $templateDir"
}

New-Item -ItemType Directory -Path $ProjectDir -Force | Out-Null
Copy-Item (Join-Path $templateDir "*") -Destination $ProjectDir -Recurse -Force

$escapedNuGetSource = [System.Security.SecurityElement]::Escape($NuGetSource)
$escapedAvaloniaVersion = [System.Security.SecurityElement]::Escape($AvaloniaVersion)
$escapedStaticLinkVersion = [System.Security.SecurityElement]::Escape($StaticLinkVersion)
$escapedStaticLinkNativeVersion = [System.Security.SecurityElement]::Escape($StaticLinkNativeVersion)

@"
<Project>
  <PropertyGroup>
    <AvaloniaVersion>$escapedAvaloniaVersion</AvaloniaVersion>
    <StaticLinkVersion>$escapedStaticLinkVersion</StaticLinkVersion>
    <StaticLinkNativeVersion>$escapedStaticLinkNativeVersion</StaticLinkNativeVersion>
  </PropertyGroup>
</Project>
"@ | Set-Content -Path (Join-Path $ProjectDir "SmokeVersions.props") -Encoding UTF8

@"
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add key="local-staticlink" value="$escapedNuGetSource" />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
  </packageSources>
</configuration>
"@ | Set-Content -Path (Join-Path $ProjectDir "NuGet.config") -Encoding UTF8
