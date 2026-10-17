# SkiaSharp 3 release line

The `skia3` branch uses the official Avalonia 12.1.4 dependencies:
SkiaSharp 3.119.4, HarfBuzzSharp 8.3.1.3, and ANGLE 2.1.27548.20260419.
Immutable source revisions are in `build/avalonia-profiles/12.1.4.json`.
The stable graphics candidate version is `3.119.4.1`. The separate macOS
`StaticLink.Avalonia.Native` candidate is `12.1.4.1`, explicitly referenced
only by applications that need it. The graphics package does not depend on it.

Use the official profile packer:

```sh
python3 scripts/pack-avalonia-profile.py --avalonia-version 12.1.4
```

## Windows 7 compatibility

Windows x64/x86 native libraries use the same compatibility recipe as `skia2`:
Zig targets Windows 7, ANGLE uses its standard mutex fallback, the C++ clock
resolves the precise clock dynamically, and GNU C++ constructors are registered
with the NativeAOT startup. Newer Windows systems retain their Avalonia UI.

On 2026-10-17 the user manually launched the x64 static NativeAOT consumer on
Windows 7 and confirmed startup and display. Its hash and the exact scope of
that manual result are recorded in `build/windows7-validation/skia3-win-x64-manual.json`.
This does not establish x86 runtime compatibility or exhaustive API coverage.

The local version tested was an overlaid development package numbered
`12.1.4.1`; the stable combined package is numbered `3.119.4.1`.

## Runtime gates and publication

The one-off release workflow builds all nine native RIDs with Zig, packs the
candidate, and publishes and runs the Avalonia NativeAOT smoke applications.
The runtime gate requires a rendered frame and normal exit. Avalonia 12 also
runs a separate macOS Metal test. Hosted Windows tests run on modern Windows;
they do not replace the manual Windows 7 compatibility check.

Earlier official-profile local and Actions runs verified real Metal rendering;
the Windows compatibility revision must pass the full workflow again.
Avalonia 11 fully static Metal remains unsupported because that Avalonia path
dynamically loads libSkiaSharp; use OpenGL or Software there.

This validation run does not publish NuGet or GitHub Releases. Daily workflows
remain disabled. Previous manual test deliveries are replaced on the next
update under `artifacts/vmware-test/`, without creating ZIP archives.

## Independent macOS Native test dependency

The graphics Actions workflow does not build or pack Avalonia.Native. Only the
macOS application smoke jobs fetch a previously validated Native package,
pinned by artifact ID and package SHA256 in
`build/avalonia-native-smoke-dependencies.json`. Windows/Linux jobs and graphics
packing do not wait for a Native build. The graphics release uploads only the
graphics package. An expired dependency artifact fails the macOS test clearly;
refresh the manifest from an independently validated Native build or package.
