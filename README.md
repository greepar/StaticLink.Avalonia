# StaticLink.Avalonia

Static native libraries for Avalonia single-file NativeAOT publishing.

## Install

```bash
dotnet add package StaticLink.Avalonia
```

Or add it manually:

```xml
<PackageReference Include="StaticLink.Avalonia" Version="3.119.4-7922.1" />
```

`3.119.4-7922.1` supports Avalonia 11. If you need the SkiaSharp 2 line for an Avalonia 11 project, use this optional package variant:

```xml
<PackageReference Include="StaticLink.Avalonia" Version="2.88.9-7151.10" />
```

`2.88.9-7151.10` is only for Avalonia 11 projects that specifically want SkiaSharp 2.

For macOS, also reference `StaticLink.Avalonia.Native`. This package is macOS-only and must match your Avalonia version because it contains `libAvaloniaNative.a`.

```xml
<PackageReference Include="StaticLink.Avalonia.Native" Version="11.3.14.1" />
```

## Publish

```bash
dotnet publish -c Release -r win-x64 \
  -p:PublishAot=true \
  -p:SelfContained=true \
  -p:PublishSingleFile=true \
  -p:StripSymbols=true
```

Use the RID you need, such as `win-x86`, `linux-x64`, `linux-arm64`, `osx-arm64`, or `osx-x64`.

For macOS, avoid the Metal renderer for fully static output. Use OpenGL or Software.

## Native Package Automation

`.github/workflows/nuget-avalonia-native.yml` runs daily and checks the latest stable `Avalonia` version on NuGet.org. If `StaticLink.Avalonia.Native.<AvaloniaVersion>.1` does not exist, it builds both macOS architectures from the matching Avalonia source tag, runs NativeAOT smoke tests, and publishes the package with NuGet Trusted Publishing.

Configure NuGet.org Trusted Publishing for this repository and the `nuget-avalonia-native.yml` workflow, then add the NuGet.org account name as the repository variable `NUGET_USER`. No long-lived NuGet API key is used by this workflow.

## Static Graphics Automation

`.github/workflows/nuget-static-graphics.yml` runs a fast version, upstream-ref, patch, script, and smoke-project preflight before starting native builds. It then calls independent Windows, Linux, Linux musl, and macOS workflows, packs their artifacts, runs all NativeAOT smoke tests, and only then publishes NuGet and GitHub Release assets.

The platform workflows can also be dispatched independently when diagnosing a single platform:

- `static-graphics-windows.yml`
- `static-graphics-linux.yml`
- `static-graphics-musl.yml`
- `static-graphics-macos.yml`

The release workflow derives the SkiaSharp version and ANGLE branch from `NuGet/StaticGraphics/StaticLink.Avalonia.csproj`. Native source and build directories are cached by platform, RID, version, patch, and build script.
