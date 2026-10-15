# StaticLink.Avalonia

Static native libraries for Avalonia single-file NativeAOT publishing.

## Install

Choose the formal package version matching your official Avalonia release. The
package pins the corresponding official SkiaSharp, HarfBuzzSharp, and ANGLE sources.

| Avalonia version | SkiaSharp version | `StaticLink.Avalonia` version |
| --- | --- | --- |
| 11.3.22 | 2.88.9 | `11.3.22.1` |
| 12.1.4 | 3.119.4 | `12.1.4.1` |

Example:
```xml
<ItemGroup>
  <PackageReference Include="Avalonia" Version="12.1.4" />
  <PackageReference Include="StaticLink.Avalonia" Version="12.1.4.1" />
</ItemGroup>
```

### macOS

For macOS, also reference `StaticLink.Avalonia.Native`. This package contains `libAvaloniaNative.a`, so its version must match the Avalonia version used by the application.

```xml
<!-- Avalonia 11.3.22 -->
<PackageReference Include="StaticLink.Avalonia.Native" Version="11.3.22.1" />

<!-- Avalonia 12.1.4 -->
<PackageReference Include="StaticLink.Avalonia.Native" Version="12.1.4.1" />
```

Add only the `StaticLink.Avalonia.Native` reference matching your Avalonia version.

The bundled C++ runtime targets macOS 13 or later. The package defaults
`AppleMinOSVersion` to `13.0` for macOS NativeAOT publishing.

On macOS, Avalonia 12 supports Metal. Avalonia 11 fully static apps must use
OpenGL or Software because its Metal path dynamically loads `libSkiaSharp`.

## Publish

```bash
dotnet publish -c Release -r win-x64 -p:PublishAot=true
```

Use the RID you need, such as `win-x86`, `linux-x64`, `linux-arm64`, `osx-arm64`, or `osx-x64`.


## Native Package Automation

The daily official release workflow validates both Avalonia version lines.
It builds all nine graphics targets and the matching macOS Avalonia.Native
archives with Zig, then publishes and runs the candidate NativeAOT applications
on every target. Avalonia 12 also requires Metal. NuGet publication is allowed
only after every required runtime test succeeds; duplicate versions are skipped.
