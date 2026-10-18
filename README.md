# StaticLink.Avalonia — skia3-daily

Tracks stable SkiaSharp 3.x and official Avalonia ANGLE for daily prereleases.

- Package: `StaticLink.Avalonia` (prerelease).
- Checks run at 10:20 Asia/Singapore; already published SkiaSharp/ANGLE pairs are skipped.
- Publication requires nine Zig targets, Avalonia 12.1.4 window/frame smoke checks and macOS Metal.

Version format: `<SkiaSharp>-<official ANGLE version>.daily.<run number>.<attempt>`. The ANGLE date is not the build date.

On macOS, reference `StaticLink.Avalonia.Native` matching your Avalonia version. Graphics packages do not force Avalonia.Desktop or Native dependencies. Avalonia 11 uses OpenGL/software; Metal requires Avalonia 12.

Select this branch for manual Actions runs. See the [project homepage](https://github.com/greepar/StaticLink.Avalonia) for package selection and usage.
