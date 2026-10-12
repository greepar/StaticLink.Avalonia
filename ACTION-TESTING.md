# Runtime-gated graphics validation

Daily graphics releases are enabled on main. All nine Avalonia runtime tests
and macOS Metal must succeed before NuGet publication. See
[RUNTIME-VALIDATION.md](RUNTIME-VALIDATION.md) for completed validation runs.
The AvaloniaNative track remains independently managed.

Before release builds, run nuget-static-graphics.yml on skia4 with
environment_only=true. This checks the actual container's Python/depot_tools,
.NET 8/10, SDKs, sysroots, and C/C++ compilation plus C executable linking for
all nine RIDs. Download toolchain-environment-validation to inspect the report.
The same environment gate runs before every graphics and native build and
must pass before the toolchain image is published for release compilation.

- skia3: nuget-static-graphics.yml; latest stable SkiaSharp 3.
- skia4: nuget-static-graphics.yml; latest stable SkiaSharp 4.
- avalonia-native: nuget-avalonia-native.yml; latest stable Avalonia 11 and 12.

Download staticlink-avalonia-nuget and avalonia-smoke-<RID> from each graphics run.
Download staticlink-avalonia-native-<version> and
avalonia-native-smoke-<AvaloniaVersion>-<RID> from the native run.
Native archives and source locks are also retained as Actions artifacts.

Graphics macOS smoke tests use the already published AvaloniaNative revision 1
by default, so the graphics builds do not require the experimental native
revision 2 to be published. The native branch validates its own local revision 2
package separately. To test both experimental packages together, put both
downloaded packages in a local NuGet feed and reference their exact versions.

Smoke executables are retained even if a later runtime validation fails.
An artifact is not evidence that all validation gates passed; check job results.

The daily-native-release workflow on main checks skia3 and skia4 every day at
02:20 UTC (10:20 Asia/Singapore), as well as supporting manual dispatch.
Use force_build=true to rebuild published versions. Existing upstream/ANGLE
versions are otherwise skipped. New candidates request NuGet publication, but
runtime-verified blocks it if a required check fails, is cancelled, or is skipped.
The NuGet Trusted Publishing policy must allow nuget-static-graphics.yml.
