# Daily SkiaSharp graphics releases

At 10:20 Asia/Singapore (02:20 UTC), main dispatches the skia3 and skia4 tracks.
Each branch checks the latest stable upstream release in its own major and skips
upstream/ANGLE combinations already published to NuGet. Manual force_build=true
can rebuild an existing version.

Every release builds nine RIDs with Zig, packs the candidate NuGet locally,
and runs an Avalonia NativeAOT application on each target. A rendered-frame
marker and successful process exit are required. The Avalonia 12 macOS Metal
check must also pass. Failed, cancelled, or skipped required validation blocks
NuGet publication through the runtime-verified job. Environment-only and
Windows-only retests cannot publish.

Trusted Publishing must allow nuget-static-graphics.yml in
greepar/StaticLink.Avalonia for StaticLink.Avalonia. The Native package has a
separate workflow and policy; it is not dispatched by this graphics schedule.
