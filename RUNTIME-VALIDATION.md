# Daily version regression validation — 2026-10-18

All five complete Actions validations succeeded with the current official ANGLE
`2.1.27548.20260419`, using the pinned Zig toolchain for all nine native targets.

| SkiaSharp | HarfBuzzSharp | Avalonia runtime baseline | Native targets | Window/Metal jobs | Actions |
| --- | --- | --- | --- | --- | --- |
| 3.119.2 | 8.3.1.3 | 11.3.22 | 9/9 | 9 passed | [39070382341](https://github.com/greepar/StaticLink.Avalonia/actions/runs/39070382341) |
| 3.119.4 | 8.3.1.5 | 12.1.4 | 9/9 | 10 passed | [39070384845](https://github.com/greepar/StaticLink.Avalonia/actions/runs/39070384845) |
| 4.150.1 | 14.2.1.1 | 12.1.4 | 9/9 | 10 passed | [39070387346](https://github.com/greepar/StaticLink.Avalonia/actions/runs/39070387346) |
| 4.150.5 | 14.2.1.5 | 12.1.4 | 9/9 | 10 passed | [39070390442](https://github.com/greepar/StaticLink.Avalonia/actions/runs/39070390442) |
| 4.153.1 | 14.2.1.301 | 12.1.4 | 9/9 | 10 passed | [39070666914](https://github.com/greepar/StaticLink.Avalonia/actions/runs/39070666914) |

The matrix passed 45 native build/link jobs and 49 Avalonia runtime jobs.
SkiaSharp 3.119.2 uses Avalonia 11.3.22, with OpenGL/software and its intended
Metal skip. The four Avalonia 12.1.4 cases include a required real Metal check.
The SkiaSharp 3.119.4 musl ARM64 build was interrupted by a GitHub runner shutdown;
rerunning the failed jobs succeeded without compiler/source changes.

macOS x64 validation uses an Intel runner; ARM64 uses Apple Silicon. Linux musl
validation uses same-architecture Alpine containers. Windows x86 uses WoW64.
Windows 7 runtime is outside this hosted matrix.

The two latest candidates were published from the exact validated artifacts;
older versions were validation-only. The publication path checks source run/jobs,
package identity, commit, dependencies and all nine native source manifests before
NuGet authentication.

| Published NuGet version | Publication Actions |
| --- | --- |
| [3.119.4-2.1.27548.20260419.daily.139.1](https://www.nuget.org/packages/StaticLink.Avalonia/3.119.4-2.1.27548.20260419.daily.139.1) | [39075079872](https://github.com/greepar/StaticLink.Avalonia/actions/runs/39075079872) |
| [4.153.1-2.1.27548.20260419.daily.143.1](https://www.nuget.org/packages/StaticLink.Avalonia/4.153.1-2.1.27548.20260419.daily.143.1) | [39075082431](https://github.com/greepar/StaticLink.Avalonia/actions/runs/39075082431) |

Both versions were verified against the public nuget.org nuspec after upload:
only exact SkiaSharp and HarfBuzzSharp dependencies; no Avalonia.Desktop or
StaticLink.Avalonia.Native dependency. Repository commits match the validated
candidate source commits.

Automatic daily checks are enabled at 02:20 UTC (10:20 Asia/Singapore).
Post-publication check-only runs for both branches returned `skip` because the
latest SkiaSharp/official ANGLE pairs are already published. New pairs must pass
the native and runtime gates before publication.
Current policy and `daily` version format are documented in [DAILY.md](DAILY.md).
Machine-readable evidence: [regression matrix](build/daily-validation/regression-matrix-2026-10-18.json).

The historical validation records below describe earlier snapshots and policies.

---

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

The existing daily graphics workflow schedules 02:20 UTC (10:20 Asia/Singapore).
It is disabled while the official Avalonia 11/12 candidates below are being
validated. Each candidate must pass the complete runtime gate before publication.
The nuget.org Trusted Publishing policies for both `StaticLink.Avalonia` and
`StaticLink.Avalonia.Native` must allow `nuget-static-graphics.yml`, which builds
and validates the matching candidates together.
The historical graphics version format uses a prerelease suffix.

The historical runs above pinned Google ANGLE chromium/7922, commit
7e08726e32026a0bbabd6ec8a1a90f5ab533ed66. This is independent of the ANGLE
version distributed by Avalonia.Angle.Windows.Natives.

## Official Avalonia package profiles

Two complete local pipelines and two Actions validations have passed:

| Avalonia | StaticLink.Avalonia | SkiaSharp | HarfBuzzSharp | Official ANGLE package |
| --- | --- | --- | --- | --- |
| 11.3.22 | 11.3.22.1 | 2.88.9 | 8.3.1.1 | 2.1.25547.20250602 |
| 12.1.4 | 3.119.4.1 | 3.119.4 | 8.3.1.3 | 2.1.27548.20260419 |

On 2026-10-15, both profiles passed all nine local native build and executable-link
checks (18/18). The Avalonia 11 graphics candidate with its pinned Native
`11.3.22.2` dependency also passed two NativeAOT application runs each on macOS
x64 (OpenGL) and Linux x64 (software), using only the main package reference.
The complete local pipeline then passed all build, pack, and runtime stages.
Avalonia 12 ran twice each on macOS x64 default/Metal (all four runs actually used
Metal) and Linux x64 (software). The ten local application runs all rendered and
exited normally. Results from the first complete pipeline are preserved under
`artifacts/validation-repeats/1`. The second complete pipeline also passed,
including fresh candidate restores, repacking, all four Native rebuilds, and
another ten successful application runs. Its reports are under
`artifacts/validation-repeats/2` (20 successful local application runs in total).

The first official-profile Actions runs also passed all nine native builds and
all nine application runtime jobs for both profiles:

- Avalonia 11.3.22: [38658792410](https://github.com/greepar/StaticLink.Avalonia/actions/runs/38658792410).
- Avalonia 12.1.4: [38658792589](https://github.com/greepar/StaticLink.Avalonia/actions/runs/38658792589), including real Metal.

The final dependency revisions passed another complete Actions validation:

- Avalonia 11.3.22 with Native 11.3.22.2: [38662866914](https://github.com/greepar/StaticLink.Avalonia/actions/runs/38662866914).
- Avalonia 12.1.4 with Native 12.1.4.1: [38662866969](https://github.com/greepar/StaticLink.Avalonia/actions/runs/38662866969), including real Metal.

Publication was not requested in any of these runs. The daily publishing workflow
remains disabled pending confirmation of the nuget.org Trusted Publishing scope.

The same package ID has two stable Avalonia version lines. The profiles under
`build/avalonia-profiles` lock official NuGet package hashes, Avalonia and Skia
commits, HarfBuzz native and managed binding commits, and the corresponding
AvaloniaUI/angle commit. Windows x86 adapters use the locked managed bindings.
Native `11.3.22.1` is already published, so the Avalonia 11 graphics candidate pins
the new Zig Native candidate `11.3.22.2`. Avalonia 12 pins Native `12.1.4.1`.
These deployment revisions are tracked separately from the compiler source locks.

On a macOS x64 host with a running Lima Debian VM, Podman in the VM, .NET, and
PowerShell, run the complete local pipeline:

```sh
caffeinate -i python3 scripts/validate-local-avalonia-profiles.py \
  --lima debian \
  --image ghcr.io/greepar/staticlink.avalonia-zig@sha256:e54b069aed7c880ea09e416886f8759df75eb283ca923dcfa37321fa3e6e9bfe
```

The repository must be mounted at the same absolute path inside Lima. Native
source checkouts use the VM's Linux filesystem, with `--work-dir` defaulting to
`/var/tmp/staticlink-avalonia-work`. The image digest is required.
`global.json` selects a stable .NET 10 SDK and excludes installed preview SDKs.

The pipeline builds and links all nine native RIDs for both profiles, builds
Avalonia.Native for both macOS architectures, verifies source provenance and
archive hashes, and packs stable candidates into local feeds. It then publishes
the existing NativeAOT smoke app and runs it twice on macOS x64 and Linux x64;
Avalonia 12 additionally requires the real Metal backend. Every failed stage
stops the pipeline. The pipeline does not upload packages.

Results are recorded in `artifacts/local-profile-validation/pipeline.json`,
`artifacts/avalonia-validation/matrix.json`, and each smoke app's
`runtime-validation.json`. Local smoke results cover macOS x64 and Linux x64.
The remaining operating-system/architecture runtime combinations must pass their
CI runners before the daily publishing workflow is enabled again.

The updated daily workflow selects the latest official stable release in each
of the 11 and 12 version lines and dispatches this same complete verification.
It runs daily even when the upstream version is unchanged; NuGet skips duplicate
versions. Manual daily dispatches default to validation without publication.
