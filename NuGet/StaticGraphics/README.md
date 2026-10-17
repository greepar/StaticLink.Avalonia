# StaticLink.Avalonia — SkiaSharp 4 daily

This branch follows the latest **stable upstream SkiaSharp 4.x** release.
Every StaticLink package from this branch is a **prerelease**, with version
`<SkiaSharp>-<official ANGLE package version>.daily.<Actions run number>.<attempt>`.
The `daily` label replaces `preview`; the package remains a NuGet prerelease.
Stable `skia2` and `skia3` package lines are maintained separately.

The resolver records exact NuGet package hashes, SkiaSharp/Skia/HarfBuzz source
commits and the matching managed HarfBuzzSharp dependency. Moving source branches
are never used. ANGLE follows the latest listed stable
`Avalonia.Angle.Windows.Natives` package by publication date. Its exact source
commit and package checksum are pinned; the historical 2.2.0 package is not
mistaken for the newest release merely because its version number sorts higher.

## Validation and publication

The `skiasharp-daily` dispatcher checks daily at 10:20 Asia/Singapore.
It starts a build only if the latest stable upstream SkiaSharp/official ANGLE pair has no
matching published StaticLink package for the same SkiaSharp/ANGLE pair. Existing in-flight
builds are skipped. Failed builds/publications are retried on a later check;
successful publication prevents rebuilding unchanged upstream pairs.
Both selected upstream versions are pinned in the dispatch inputs.
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

## Version regression checks

The initial regression matrix covers SkiaSharp 3.119.2, 3.119.4, 4.150.1,
4.150.5 and 4.153.1. Each selected version has an independent nine-target build
and Avalonia NativeAOT runtime gate. Older versions are validation-only.
SkiaSharp 3.119.2 uses Avalonia 11.3.22 because current Avalonia 12.1.4 requires
SkiaSharp >= 3.119.4. All daily publications continue to require Avalonia 12.1.4
and the real Metal check; the older baseline cannot publish a daily package.
A new upstream version is resolved from its own package/source provenance and
must pass the whole runtime gate before it can be published. This is not a
claim that all future ABI or build changes will work without adaptation.
