# StaticLink.Avalonia

Static native libraries for Avalonia single-file NativeAOT publishing.

## Install

Choose the static graphics package that matches the Avalonia and SkiaSharp major versions used by your application.

| Avalonia version | SkiaSharp version | `StaticLink.Avalonia` version |
| --- | --- | --- |
| 11.3.14 | 2.88.9 | `2.88.9-7151.10` |
| 11.3.14 | 3.119.4 | `3.119.4-7922.1` |
| 12.1.0 | 3.119.4 | `3.119.4-7922.1` |
| 12.1.0 | 4.150.1 | `4.150.1-7922.1` |

### Avalonia 11 with SkiaSharp 2

```xml
<ItemGroup>
  <PackageReference Include="Avalonia" Version="11.3.14" />
  <PackageReference Include="Avalonia.Desktop" Version="11.3.14" />
  <PackageReference Include="Avalonia.Themes.Fluent" Version="11.3.14" />
  <PackageReference Include="StaticLink.Avalonia" Version="2.88.9-7151.10" />
</ItemGroup>
```

### Avalonia 11 with SkiaSharp 3

```xml
<ItemGroup>
  <PackageReference Include="Avalonia" Version="11.3.14" />
  <PackageReference Include="Avalonia.Desktop" Version="11.3.14" />
  <PackageReference Include="Avalonia.Themes.Fluent" Version="11.3.14" />
  <PackageReference Include="StaticLink.Avalonia" Version="3.119.4-7922.1" />
</ItemGroup>
```

### Avalonia 12 with SkiaSharp 3

```xml
<ItemGroup>
  <PackageReference Include="Avalonia" Version="12.1.0" />
  <PackageReference Include="Avalonia.Desktop" Version="12.1.0" />
  <PackageReference Include="Avalonia.Themes.Fluent" Version="12.1.0" />
  <PackageReference Include="StaticLink.Avalonia" Version="3.119.4-7922.1" />
</ItemGroup>
```

### Avalonia 12 with SkiaSharp 4

```xml
<ItemGroup>
  <PackageReference Include="Avalonia" Version="12.1.0" />
  <PackageReference Include="Avalonia.Desktop" Version="12.1.0" />
  <PackageReference Include="Avalonia.Themes.Fluent" Version="12.1.0" />
  <PackageReference Include="StaticLink.Avalonia" Version="4.150.1-7922.1" />
</ItemGroup>
```

### macOS

For macOS, also reference `StaticLink.Avalonia.Native`. This package contains `libAvaloniaNative.a`, so its version must match the Avalonia version used by the application.

```xml
<!-- Avalonia 11.3.14 -->
<PackageReference Include="StaticLink.Avalonia.Native" Version="11.3.14.1" />

<!-- Avalonia 12.1.0 -->
<PackageReference Include="StaticLink.Avalonia.Native" Version="12.1.0.1" />
```

Add only the `StaticLink.Avalonia.Native` reference matching your Avalonia version.

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
