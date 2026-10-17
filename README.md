# StaticLink.Avalonia

Static native libraries for Avalonia single-file NativeAOT publishing.

## Install

Choose the static graphics package that matches the Avalonia and SkiaSharp major versions used by your application.

| Avalonia version | SkiaSharp version | `StaticLink.Avalonia` version |
| --- | --- | --- |
| 11 | 2.88.9 | `2.88.9-7151.10` |
| 11 | 3.119.4 | `3.119.4-7922.1` |
| 12 | 3.119.4 | `3.119.4-7922.1` |
| 12 | 4.150.1 | `4.150.1-7922.1` |

Example:
```xml
<ItemGroup>
  <PackageReference Include="Avalonia" Version="12.1.0" />
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

On macOS, only Avalonia 12 with skia3/4 supports Metal. Avalonia 11 fully static apps must use OpenGL or Software because its Metal path dynamically loads `libSkiaSharp`.

## Publish

```bash
dotnet publish -c Release -r win-x64 -p:PublishAot=true
```

Use the RID you need, such as `win-x86`, `linux-x64`, `linux-arm64`, `osx-arm64`, or `osx-x64`.


## Native Package Automation

`.github/workflows/nuget-avalonia-native.yml` runs daily and checks the latest stable `Avalonia` version on NuGet.org. If `StaticLink.Avalonia.Native.<AvaloniaVersion>.1` does not exist, it builds both macOS architectures from the matching Avalonia source tag, runs NativeAOT smoke tests, and publishes the package with NuGet Trusted Publishing.
