# StaticLink.Avalonia

Static native libraries for Avalonia NativeAOT single-file applications.
This branch contains documentation and daily dispatchers; builds live on the release branches.

## Package lines

| Branch | Purpose | Package version |
| --- | --- | --- |
| [skia2](https://github.com/greepar/StaticLink.Avalonia/tree/skia2) | Stable SkiaSharp 2 | `2.88.9.1` |
| [skia3](https://github.com/greepar/StaticLink.Avalonia/tree/skia3) | Stable SkiaSharp 3 | `3.119.4.1` |
| [skia3-daily](https://github.com/greepar/StaticLink.Avalonia/tree/skia3-daily) | SkiaSharp 3 prereleases | `3.119.4-2.1.27548.20260419.daily.139.1` |
| [skia4-daily](https://github.com/greepar/StaticLink.Avalonia/tree/skia4-daily) | SkiaSharp 4 prereleases | `4.153.1-2.1.27548.20260419.daily.143.1` |
| [avalonia-native](https://github.com/greepar/StaticLink.Avalonia/tree/avalonia-native) | Separate macOS Native library | `StaticLink.Avalonia.Native`, matching your Avalonia version |

All graphics lines use the NuGet package ID [StaticLink.Avalonia](https://www.nuget.org/packages/StaticLink.Avalonia).
Prefer stable packages for normal use. Graphics packages pin SkiaSharp/HarfBuzzSharp;
choose a compatible Avalonia version separately. Avalonia.Desktop and the Native package are not forced dependencies.

## Usage

```xml
<ItemGroup>
  <PackageReference Include="Avalonia.Desktop" Version="12.1.4" />
  <PackageReference Include="StaticLink.Avalonia" Version="3.119.4.1" />
</ItemGroup>
```

On macOS, also reference `StaticLink.Avalonia.Native` matching your Avalonia version.
Keep older Native packages available for their corresponding Avalonia releases.
Avalonia 11 uses OpenGL/software; Metal requires Avalonia 12.

```bash
dotnet publish -c Release -r win-x64 -p:PublishAot=true
```

## Daily builds

Checks run at **10:20 Asia/Singapore**. They track stable SkiaSharp and the latest
published stable official ANGLE package. Already published pairs are skipped.
New pairs must pass nine Zig targets, Avalonia 12.1.4 runtime smoke checks and macOS Metal before publication.

Version format: `<SkiaSharp>-<official ANGLE version>.daily.<run number>.<attempt>`.
`20260419` belongs to the ANGLE version, not the daily build date.

The separate Native schedule currently validates and uploads Actions artifacts;
publication is controlled independently. For manual builds, select the release branch under **Run workflow**.

## Superseded prereleases

`2.88.9-7151.10`, `3.119.2-7151.10`, `3.119.2-7151.11`, `3.119.2-7151.12`,
`3.119.4-7922.1` and `4.150.1-7922.1` are superseded and may be unlisted.
Existing projects can still restore unlisted packages by exact version.
