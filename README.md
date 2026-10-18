# StaticLink.Avalonia — skia3

Stable SkiaSharp 3 graphics package branch.

- Package: `StaticLink.Avalonia` [3.119.4.1](https://www.nuget.org/packages/StaticLink.Avalonia/3.119.4.1).
- SkiaSharp: `3.119.4`. Choose an Avalonia version compatible with the pinned SkiaSharp/HarfBuzzSharp dependencies.
- Zig builds and Avalonia NativeAOT smoke checks cover nine targets before publication.

On macOS, reference `StaticLink.Avalonia.Native` matching your Avalonia version. Graphics packages do not force Avalonia.Desktop or Native dependencies. Avalonia 11 uses OpenGL/software; Metal requires Avalonia 12.

Select this branch for manual Actions runs. See the [project homepage](https://github.com/greepar/StaticLink.Avalonia) for package selection and usage.
