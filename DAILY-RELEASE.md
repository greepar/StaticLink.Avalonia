# Daily graphics releases

The dispatcher on main checks the latest stable SkiaSharp 3 and 4 every day.
Existing upstream/ANGLE versions are skipped; force_build can rebuild them.
NuGet publication requires all nine Zig builds, package checks, all nine Avalonia
NativeAOT applications to render and exit successfully, and the macOS Metal test.
A failed, cancelled, or skipped runtime check blocks publication. Windows-only
retests and environment-only runs cannot authorize publication.

NuGet Trusted Publishing must allow greepar/StaticLink.Avalonia and the workflow
nuget-static-graphics.yml for the StaticLink.Avalonia package.
