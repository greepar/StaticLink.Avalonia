# StaticLink.Avalonia — SkiaSharp 3 daily

This branch follows the latest **stable upstream SkiaSharp 3.x** release.
Every StaticLink package from this branch is a **preview**, with version
`<SkiaSharp>-preview.<UTC date>.<Actions run ID>.<attempt>`.
Stable `skia2` and `skia3` package lines are maintained separately.

The resolver records exact NuGet package hashes, SkiaSharp/Skia/HarfBuzz source
commits and the matching managed HarfBuzzSharp dependency. Moving source branches
are never used. ANGLE remains pinned to official Avalonia 12.1.4:
`2.1.27548.20260419` (`1c89805903c1482166356d3b950d474973180e61`).

## Validation and publication

The `skiasharp-daily` dispatcher runs daily at 10:20 Asia/Singapore and starts
`nuget-static-graphics.yml` on `skia3-daily` and `skia4-daily` independently.
Nine native targets are built with the pinned Zig toolchain on Linux.
Avalonia **12.1.4** NativeAOT window/frame tests must pass on all nine targets;
macOS ARM64 must additionally pass the real Metal check before NuGet publication.
macOS x64 uses `macos-15-intel`, ARM64 uses `macos-15`. Linux musl tests run in
same-architecture Alpine containers. Windows x86 runs under WoW64 on x64 Windows.
A failed, skipped or cancelled required check blocks publication.

The graphics package fixes SkiaSharp and HarfBuzzSharp, and does not depend on
Avalonia.Desktop or StaticLink.Avalonia.Native. Applications select Avalonia.
For macOS, reference the separate Native package matching your Avalonia version.
Daily smoke tests reuse an independently validated, checksum-pinned Native
package; they do not build or publish it as part of the graphics workflow.

Passing this matrix establishes the selected runtime baseline, not compatibility
with every Avalonia version or Windows 7. Avalonia 11 Metal is not patched.
New upstream API/build changes fail closed and require adaptation.
