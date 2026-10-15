# Official Avalonia validation

The stable release pipeline is `nuget-static-graphics.yml`. Select
`avalonia_version=11.3.22` or `avalonia_version=12.1.4` and leave publication
inputs false to validate without uploading NuGet packages.

Every native archive is built with Zig in the pinned Linux toolchain image,
including the matching Avalonia.Native archives for both macOS architectures.
The candidate packages are packed locally and then used by all nine NativeAOT
application runtime jobs. A rendered-frame marker and normal exit are required.
Avalonia 12 additionally requires the actual Metal backend. Failed, cancelled,
or skipped required checks block publication.

The same package ID has stable versions `11.3.22.1` and `12.1.4.1`. Source
locks come from official Avalonia, SkiaSharp, HarfBuzzSharp, and ANGLE packages.
See [RUNTIME-VALIDATION.md](RUNTIME-VALIDATION.md) for evidence and the local
Lima/Podman validation command.

Download `staticlink-avalonia-nuget`, `graphics-release-source-lock`, and
`avalonia-smoke-<RID>` artifacts from the run. The NuGet artifact includes the
matching `StaticLink.Avalonia.Native` candidate. An uploaded artifact alone does
not establish success; check the `runtime-verified` job.

Daily official release validation remains disabled until these candidates pass
local and Actions validation. Manual daily dispatch defaults to validation
without publication. Scheduled validation will run both version lines every day
at 02:20 UTC (10:20 Asia/Singapore) and skip duplicate NuGet uploads.

Historical `skia3` and `skia4` branch workflows remain available through the
SkiaSharp profile input. The independent `avalonia-native` branch and its daily
artifact checks remain separate from the official graphics release pipeline.
