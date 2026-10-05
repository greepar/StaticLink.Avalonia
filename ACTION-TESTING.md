# Manual artifact validation

Native daily checks are enabled by daily-avalonia-native.yml on main at 03:17
UTC (11:17 Singapore time). Skia3/4 daily schedules remain disabled. No
NuGet.org publication or GitHub Release is requested by either dispatcher.

The Native checker handles the latest stable Avalonia 11 and 12 independently.
It skips versions with non-expired NuGet artifacts from a successful Native
run at the current avalonia-native branch commit. New versions, changed Native
code, expired artifacts, or failed builds trigger a new artifact-only build.
Set force_build=true on the daily checker to bypass this successful-run check.

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

The daily-native-release workflow on main currently supports manual dispatch
only. Its three matrix jobs check out their own branch and dispatch independently.
Use force_build=true to rebuild published versions for testing.
After validation, enable the schedule on main only; non-default branches cannot
run their own GitHub cron schedules. Publication remains an explicit opt-in.
The manual graphics dispatcher still checks publication rather than successful
Actions runs. Add the same successful-run tracking before enabling artifact-only
daily graphics builds if avoiding repeated builds is required.
