# StaticLink.Avalonia

Static native libraries for Avalonia single-file NativeAOT publishing.

## Install

Choose the package line matching the SkiaSharp version used by your application.
All four lines use the same NuGet package ID, `StaticLink.Avalonia`.

| Branch / channel | SkiaSharp | Current package version | Typical Avalonia use |
| --- | --- | --- | --- |
| `skia2` / stable | 2.88.9 | [`2.88.9.1`](https://www.nuget.org/packages/StaticLink.Avalonia/2.88.9.1) | Avalonia 11 with SkiaSharp 2 |
| `skia3` / stable | 3.119.4 | [`3.119.4.1`](https://www.nuget.org/packages/StaticLink.Avalonia/3.119.4.1) | Avalonia 11 with SkiaSharp 3, or Avalonia 12 |
| `skia3-daily` / prerelease | 3.119.4 | [`3.119.4-2.1.27548.20260419.daily.139.1`](https://www.nuget.org/packages/StaticLink.Avalonia/3.119.4-2.1.27548.20260419.daily.139.1) | Daily validation baseline: Avalonia 12.1.4 |
| `skia4-daily` / prerelease | 4.153.1 | [`4.153.1-2.1.27548.20260419.daily.143.1`](https://www.nuget.org/packages/StaticLink.Avalonia/4.153.1-2.1.27548.20260419.daily.143.1) | Daily validation baseline: Avalonia 12.1.4 |

Prefer the stable lines for normal use. Enable prerelease versions in your NuGet
client to select a daily package. Package versions follow SkiaSharp, not Avalonia.
The graphics package pins its matching SkiaSharp and HarfBuzzSharp dependencies;
it does not depend on `Avalonia.Desktop` or `StaticLink.Avalonia.Native`.
Choose your Avalonia version separately and ensure its dependency requirements
are compatible with those pinned versions. This table does not guarantee every
Avalonia/SkiaSharp combination.

Example using the stable SkiaSharp 3 line:

```xml
<ItemGroup>
  <PackageReference Include="Avalonia.Desktop" Version="12.1.4" />
  <PackageReference Include="StaticLink.Avalonia" Version="3.119.4.1" />
</ItemGroup>
```

### Superseded prereleases

The following older prereleases have been superseded and may be unlisted:

- `2.88.9-7151.10`
- `3.119.2-7151.10`, `3.119.2-7151.11`, `3.119.2-7151.12`
- `3.119.4-7922.1`
- `4.150.1-7922.1`

For new projects, use one of the current lines above. Unlisting hides a version
from normal discovery; existing projects can still restore it by exact version.
`StaticLink.Avalonia.Native` versions are maintained separately: older versions
can still be needed by applications using the matching Avalonia release.

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


## Daily graphics packages

`skiasharp-daily` ([workflow](.github/workflows/daily-native-release.yml)) checks
at **10:20 Asia/Singapore (02:20 UTC)** each day. It tracks the latest stable
SkiaSharp release in each major line and the latest listed stable official
`Avalonia.Angle.Windows.Natives` package by publication date. An unchanged
SkiaSharp/ANGLE pair with an existing published package is skipped.

Daily version format:

```text
<SkiaSharp>-<official ANGLE package version>.daily.<Actions run number>.<attempt>
```

For example, `20260419` in the current daily versions belongs to the official
ANGLE version `2.1.27548.20260419`; it is not the daily build date. The hyphen
makes these NuGet prereleases even without a `preview` label.

New pairs must pass all nine Zig native build/link targets, all nine Avalonia
12.1.4 NativeAOT window/frame checks and the required macOS Metal check before
publication. Failed required checks block publication. The initial regression
matrix passed SkiaSharp 3.119.2, 3.119.4, 4.150.1, 4.150.5 and 4.153.1; the older
3.119.2 validation used Avalonia 11.3.22. See the
[validation evidence](https://github.com/greepar/StaticLink.Avalonia/blob/skia4-daily/RUNTIME-VALIDATION.md).
Future upstream changes must pass these gates; this is not a guarantee of
compatibility with all future releases or Windows 7.

## Native Package Automation

`osx-native-daily` ([workflow](.github/workflows/daily-avalonia-native.yml)) checks
the latest stable Avalonia 11 and 12 releases independently. It dispatches the
separate macOS Native workflow when a matching package is missing. Native
packages are built from the matching Avalonia source, validated with NativeAOT
smoke tests and published separately from the graphics package.
