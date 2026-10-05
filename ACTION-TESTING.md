# Manual artifact validation

Daily schedules are disabled during validation. No NuGet.org publication or
GitHub Release is requested by the manual dispatcher on main.

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
While publication is disabled, an unpublished package may be rebuilt on every
check; add successful-run tracking before enabling artifact-only daily builds
if avoiding repeated builds is required.

