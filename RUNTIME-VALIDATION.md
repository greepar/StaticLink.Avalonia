# Validated graphics builds

Full Actions validation completed on 2026-10-13 (Asia/Singapore):

| Track | SkiaSharp | Run |
| --- | --- | --- |
| skia3 | 3.119.4 | [38291443171](https://github.com/greepar/StaticLink.Avalonia/actions/runs/38291443171) |
| skia4 | 4.150.1 | [38291448114](https://github.com/greepar/StaticLink.Avalonia/actions/runs/38291448114) |
| skia4 | 4.153.1 | [38292705306](https://github.com/greepar/StaticLink.Avalonia/actions/runs/38292705306) |

Each run passed all nine RID build jobs, candidate NuGet packing, all nine
Avalonia 11.3.14 NativeAOT application runtime tests, and the Avalonia 12.1.0
macOS arm64 default/Metal test. Native archive caches were reused; applications
were published and executed again. Runtime success requires a rendered-frame
marker and normal process exit. These were validation-only runs: the actual
NuGet push and Trusted Publishing login steps were skipped.

The Windows runtime logs report an OpenGL Skia backend. The ordinary Linux and
macOS tests can use software rendering; only the Metal test requires Metal.
This establishes startup/rendering for these test combinations, not coverage
of every application feature or every graphics driver.

Daily graphics releases are enabled on main at 02:20 UTC (10:20 Asia/Singapore).
Each new candidate must pass the same runtime gate before publication. The
nuget.org Trusted Publishing policy must allow nuget-static-graphics.yml.
The graphics package version format currently retains its prerelease suffix.

ANGLE sources remain pinned to Google ANGLE chromium/7922, commit
7e08726e32026a0bbabd6ec8a1a90f5ab533ed66. This is independent of the ANGLE
version distributed by Avalonia.Angle.Windows.Natives.
