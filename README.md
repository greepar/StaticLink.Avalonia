# StaticLink.Avalonia

Static native libraries for Avalonia NativeAOT single-file applications.
This branch contains documentation and daily dispatchers; builds live on the release branches.

## Usage

Choose a stable package for your Avalonia version:

- **Avalonia 11:** prefer `StaticLink.Avalonia` **`2.88.9.1`** (SkiaSharp 2). If your application already uses SkiaSharp 3, use **`3.119.4.1`** instead.
- **Avalonia 12:** prefer `StaticLink.Avalonia` **`3.119.4.1`** (SkiaSharp 3).

Use daily prereleases only when you need newer upstream graphics libraries, and ensure your Avalonia dependencies are compatible.

Example for Avalonia 12:

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

## Branches

| Branch | Purpose |
| --- | --- |
| [main](https://github.com/greepar/StaticLink.Avalonia/tree/main) | Project documentation and daily build dispatchers. Select a release branch for actual builds. |
| [skia2](https://github.com/greepar/StaticLink.Avalonia/tree/skia2) | Stable SkiaSharp 2 graphics packages, recommended for Avalonia 11 using SkiaSharp 2. |
| [skia3](https://github.com/greepar/StaticLink.Avalonia/tree/skia3) | Stable SkiaSharp 3 graphics packages, recommended for Avalonia 12 and Avalonia 11 applications using SkiaSharp 3. |
| [skia3-daily](https://github.com/greepar/StaticLink.Avalonia/tree/skia3-daily) | Tracks the latest stable upstream SkiaSharp 3 and official Avalonia ANGLE; publishes daily prereleases after build and runtime checks. |
| [skia4-daily](https://github.com/greepar/StaticLink.Avalonia/tree/skia4-daily) | Tracks the latest stable upstream SkiaSharp 4 and official Avalonia ANGLE; publishes daily prereleases after build and runtime checks. |
| [avalonia-native](https://github.com/greepar/StaticLink.Avalonia/tree/avalonia-native) | Builds the separate macOS `StaticLink.Avalonia.Native` library for the matching Avalonia version. |

All Skia branches use the package ID `StaticLink.Avalonia`. Daily checks run at 10:20 Asia/Singapore and skip already published SkiaSharp/ANGLE pairs. New pairs must pass nine Zig build targets, Avalonia 12.1.4 runtime smoke checks and macOS Metal before publication.
