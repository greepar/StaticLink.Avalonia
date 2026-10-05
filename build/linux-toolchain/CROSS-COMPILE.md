# Zig cross compilation for SkiaSharp 3 / 4

All nine native targets use Zig 0.14.1 from Linux: linux-x64, linux-arm64,
linux-musl-x64, linux-musl-arm64, win-x64, win-x86, win-arm64, osx-x64, osx-arm64.
Windows uses the GNU ABI, without MSVC. macOS uses a checksum-pinned real SDK,
without Xcode. AvaloniaNative 11/12 also compiles with Zig on Linux.

## Local evidence (2026-10-04)

| Check | Result |
| --- | --- |
| 3.119.2, 3.119.4, 4.150.3, 4.150.5, 4.153.1 × nine GN configurations | 45 passed; these are configuration checks |
| All five versions, Windows x64 Skia/SkiaSharp/HarfBuzz compilation and executable link | Passed |
| 3.119.4 Windows x86 Skia and stdcall thunks | Compilation and raster/EGL links passed; fixed ANGLE archives reused |
| 3.119.4 Linux x64 | All six archives and both links passed; raster/UTF-8 execution passed |
| 3.119.4 Linux ARM64 | Three Skia archives and raster link passed; raster/UTF-8 execution passed under QEMU |
| 4.153.1 macOS ARM64 | Three Skia archives and raster executable link passed |
| AvaloniaNative 11.3.14 / 12.1.0, both macOS architectures | Four full compilations and SDK libc++ executable links passed |

Exact scope is recorded in `recent-version-validation.json`. Earlier baseline
results are retained separately. The raster probe checks 64 pixels and UTF-8
buffer ingestion; it does not prove complete font shaping or GPU operation.

There is no local Docker daemon or Windows/macOS runtime. The complete Debian
image, five releases × nine full builds, NativeAOT consumer applications and
actual Actions/NuGet publication have not been verified locally. Local builds
used the Linux host and pinned cross tools, not a running Debian container.

## Repeatable inputs and failure policy

`Dockerfile` pins Debian 12 by digest, apt by snapshot and depot_tools by commit.
`Dockerfile.cross-probe` is the production cross image despite its historical
name. It pins Zig, the macOS SDK, WinRT headers, availability runtime and Linux
sysroot packages by checksum. SDK extraction supports pinned Debian Python 3.11.

`zig-toolchain-image.yml` builds/reuses GHCR images by recipe digest and passes
an immutable image digest to downstream builds. Repository package write
permission is required. Source profiles pin SkiaSharp, Skia and ANGLE commits.
Verified native archives use an exact per-version/RID/image/recipe cache key.
A hit skips source preparation and native compilation, while consumer tests still
run. Failed native builds save a compiler cache capped at 128 MiB; they do not
save the multi-gigabyte source trees or Zig global cache. ccache additionally
checks compiler contents. Cold source downloads remain necessary on archive
cache misses, and cache eviction can still require a rebuild.

`build-cross.py` adapts declared GN capabilities, rejects unknown compiler flags,
checks static targets, builds six archives and links raster and EGL/GLES probes.
`package-zig.py` requires archive hashes and successful links before packaging.
Windows x86 gets generated stdcall thunks. Captured Zig runtime libraries are
included for consumer linking. A successful C link does not establish NativeAOT
compatibility; the release workflow gates publication on consumer OS tests.

## Run

Use the `zig-recent-regression` manual Action for recent-version full matrices.
Use `static-graphics-zig-cross-debian12` for one pinned release and nine RIDs.
For already synced sources, run `build/linux-toolchain/build-cross.py --help`;
`--configure-only` configures without compiling, while `--component skia` checks
only the three Skia libraries and their executable link.

This common driver supports the tested source revisions. Future compiler,
SDK, GN or source changes can still require deliberate updates. Daily releases
fail closed and publish only after all required jobs pass. SkiaSharp 2 is frozen
and excluded from the new regression/release tracks.
