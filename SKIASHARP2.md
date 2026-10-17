# SkiaSharp 2 release line

The `skia2` branch maintains the StaticLink.Avalonia release line for
Avalonia 11 with its official SkiaSharp 2 dependency. Windows 7 compatibility
is one verified capability of this line, not a separate UI or package product.

## Locked release candidate

| Component | Version |
| --- | --- |
| Avalonia | 11.3.22 |
| SkiaSharp | 2.88.9 (Skia m88) |
| HarfBuzzSharp | 8.3.1.1 |
| Official ANGLE source profile | 2.1.25547.20250602 |
| Main package | StaticLink.Avalonia 2.88.9.1 |
| Separate macOS native package (explicit reference) | StaticLink.Avalonia.Native 11.3.22.2 |

Source revisions are pinned in `build/avalonia-profiles/11.3.22.json`. Use the
profile packer rather than a bare pack of the historical generic project:

```sh
python3 scripts/pack-avalonia-profile.py --avalonia-version 11.3.22
```

Avalonia controls, themes and platform window features remain those provided
by Avalonia 11 on the running OS. The Windows compatibility changes affect
native time queries and ANGLE mutex implementation; they do not select a
Windows 7 visual theme. The compatibility build uses standard mutexes on all
Windows versions. Its C++ clock selects the precise time API when available.

## Validation and publication status

- The original official profile passed nine native target builds and target
  runtime checks in Actions before the Windows compatibility changes.
- The updated Windows x64 and x86 native libraries and consumer applications
  passed local Win7 SP1 x64 tests. Each final consumer passed five consecutive
  OpenGL rendered-frame/normal-exit checks; x86 was run through WoW64.
- These results cover startup and rendered frames, not every UI feature or
  hardware configuration. See `WINDOWS7-VALIDATION.md` and committed evidence
  in `build/windows7-validation/`.
- The changed recipe/targets still require the complete release workflow on
  this revision before the combined nine-RID package can be published. Do not
  label the entire changed package as fully validated based on the earlier
  Actions runs alone.
- No NuGet upload has occurred. Both daily workflows remain disabled.
  A one-off complete Actions validation is authorized without publication.
- Before uploading, confirm the NuGet Trusted Publishing policy permits
  `nuget-static-graphics.yml` for the `StaticLink.Avalonia*` package scope.

The existing official Avalonia 12 / SkiaSharp 3 profile remains available in
the repository; it is a separate release line and is not the SkiaSharp 2
candidate described here.
