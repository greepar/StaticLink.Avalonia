# Local verification in the CI image

Run from the repository checkout with Docker (including OrbStack). Use the exact
immutable digest reported by the CI `environment / image` job:

```sh
python3 scripts/validate-container-matrix.py \
  --image ghcr.io/greepar/staticlink.avalonia-zig@sha256:064f7242871946f6aa24406ba8d0eed227efee6bce089526324199640308e3f2
```

On a Mac with a local HTTP proxy that containers do not inherit, add
`--proxy http://host.docker.internal:7897` (use the actual configured port).
This changes network routing only; TLS verification and locked revisions remain
required. depot_tools metrics are disabled to avoid network detection during
its command startup.

The default matrix is the latest three stable releases of each major checked
on 2026-10-05: 3.119.1, 3.119.2, 3.119.4, 4.152.3, 4.153.0 and 4.153.1, each for
all nine RIDs. Exact upstream tags and their Skia gitlinks are locked in
`versions/`. Use `--versions`, `--rids` or `--jobs` to choose a subset.

The runner executes the environment gate, prepares locked sources, then calls
the same `build-cross.py` and `package-zig.py` used by CI. It requires complete
Skia/SkiaSharp/HarfBuzz and ANGLE/EGL/GLES archives plus both executable link
tests before recording a passed target. Logs, packaged archives and the current
machine-readable result are under `artifacts/container-validation/`.
`matrix.json` is updated after every target, and reruns skip successful targets
for the same image. Intermediates and compiler caches use a Docker volume to
avoid macOS bind-mount overhead. The compiler cache is capped at 20 GB and
normalizes workspace paths so unchanged inputs can be reused across minor
versions. Compiler wrapper contents are hashed; the underlying Zig binary is
pinned by the immutable image. Failed targets can be resumed.

This verifies native compilation and executable linking. Windows/macOS runtime
and NativeAOT consumer applications still need the release workflow's OS tests.

# Image reuse

The GHCR recipe key includes both Dockerfiles, the sysroot downloader and locks,
and the adapter/environment probes copied into the image. Release profiles,
source locks, build drivers, GN templates and project patches run from the
checked-out workspace and do not create another SDK image. Toolchain changes
still create an image with a new recipe tag; consumers always use its digest.

Image jobs share a repository concurrency group with `queue: max`, so simultaneous
Skia 3/4 builds wait and reuse the published image. Missing manifests trigger a
build; registry/network/authentication errors retry and then fail rather than
being mistaken for a missing image.

GitHub documents `queue: max`, but actionlint 1.7.12 does not yet recognize that
key. Validate with this narrowly scoped ignore until actionlint supports it:

```sh
actionlint -shellcheck= -pyflakes= \
  -ignore 'unexpected key "queue" for "concurrency" section' .github/workflows/*.yml
```

Reference: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency
