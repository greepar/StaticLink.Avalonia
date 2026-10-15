# Daily official Avalonia releases

The `daily-native-release.yml` workflow selects the latest official stable
Avalonia release in each of the 11 and 12 version lines. Both use the same
`StaticLink.Avalonia` package ID, with formal versions `<AvaloniaVersion>.1`.
It dispatches `nuget-static-graphics.yml` on the current default branch.

The workflow is currently disabled while the first candidates are validated.
After validation it runs at 02:20 UTC (10:20 Asia/Singapore). Each daily run
validates both lines, even if the upstream version is unchanged. NuGet skips
duplicate versions. Manual dispatch defaults to validation without publication.

Publication requires all nine Zig target builds, matching Avalonia.Native
archives, package provenance and hash checks, and a real Avalonia NativeAOT
application rendering and exiting normally on every target. Avalonia 12 also
requires Metal. A failed, cancelled, or skipped required test blocks publishing.
Environment-only and Windows-only retests cannot publish.

Trusted Publishing must allow `greepar/StaticLink.Avalonia` and
`nuget-static-graphics.yml` for both the `StaticLink.Avalonia` and
`StaticLink.Avalonia.Native` packages, which are validated together.

The separate Native artifact-only schedule is retained for its historical
branch; it does not publish NuGet packages.
