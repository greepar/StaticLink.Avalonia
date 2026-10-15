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

The first complete local pipeline and two Actions validations have passed:

| Avalonia | StaticLink.Avalonia | SkiaSharp | HarfBuzzSharp | Official ANGLE package |
| --- | --- | --- | --- | --- |
| 11.3.22 | 11.3.22.1 | 2.88.9 | 8.3.1.1 | 2.1.25547.20250602 |
| 12.1.4 | 12.1.4.1 | 3.119.4 | 8.3.1.3 | 2.1.27548.20260419 |

On 2026-10-15, both profiles passed all nine local native build and executable-link
checks (18/18). The Avalonia 11 graphics candidate with its pinned Native
`11.3.22.2` dependency also passed two NativeAOT application runs each on macOS
x64 (OpenGL) and Linux x64 (software), using only the main package reference.
The complete local pipeline then passed all build, pack, and runtime stages.
Avalonia 12 ran twice each on macOS x64 default/Metal (all four runs actually used
Metal) and Linux x64 (software). The ten local application runs all rendered and
exited normally. Results from the first complete pipeline are preserved under
`artifacts/validation-repeats/1`. A second complete pipeline is in progress.

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
