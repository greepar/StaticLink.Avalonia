# Debian 12 Zig cross toolchain

The production native-build path is the pinned Debian 12 image plus Zig 0.14.1,
covering all nine GNU Linux, musl Linux, Windows and macOS targets. musl uses
checksum-locked target sysroots inside the same Debian image.

Read [CROSS-COMPILE.md](CROSS-COMPILE.md) for current build commands, exact local
validation scope and remaining Docker/runtime/NativeAOT verification. Read
[DAILY-RELEASE.md](../../DAILY-RELEASE.md) for daily 3/4 release configuration.

`Dockerfile` pins the base digest, apt snapshot and source-preparation tools.
`Dockerfile.cross-probe` adds Zig, macOS SDK, Windows headers, target Linux SDKs
and .NET SDKs. The historical filename is retained for existing references.
`zig-toolchain-image.yml` reuses recipe-tagged GHCR images and downstream jobs
pull their immutable digest. Source locks and archive/link manifests provide
traceability. See [CONTAINER-VALIDATION.md](CONTAINER-VALIDATION.md) for
local OrbStack verification using the exact immutable CI image.

Legacy platform helper scripts are retained for reference; production graphics
Actions now delegate to the common Zig cross-build workflow. SkiaSharp 2 remains
outside the new daily tracks.
