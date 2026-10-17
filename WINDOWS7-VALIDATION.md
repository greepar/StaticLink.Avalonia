# Windows 7 follow-up validation

Validated on 2026-10-16 against Avalonia 11.3.22 and a local StaticLink.Avalonia 11.3.22.1 candidate. This candidate has not been published to NuGet.

## Fixes

- Zig native targets for Windows x64/x86 specify `windows.win7`. This selects libc++'s upstream dynamic clock lookup and `GetSystemTimeAsFileTime` fallback.
- The compiler adapter defines `ANGLE_WINDOWS_NO_FUTEX` for all translation units in those targets. ANGLE uses its standard mutex implementation instead of importing `WaitOnAddress` and `WakeByAddressSingle`.
- Windows cross publishing can run the existing COFF initialization conversion through `pwsh` on macOS. This conversion also registers the Win7 clock fallback constructor with CRT startup.
- AotAnywhere cross linking uses Zig's CRT/builtins and avoids MSVC-only library aliases. Static graphics are added before the AotAnywhere link takeover.
- Package overlays preserve original ZIP timestamps and use UTC for new entries. This prevents restored libraries from being eight hours in the future in Singapore, which otherwise causes the SDK to run its native Windows linker after AotAnywhere already linked successfully.

## Actual build and run

- Native graphics: local Lima/Podman Linux container, pinned Zig 0.14.1, `x86_64-windows.win7-gnu`; locked official Avalonia 11.3.22 sources.
- Consumer: macOS x64, .NET SDK 10.0.401, .NET runtime 10.0.11, AotAnywhere 1.1.0. The external host Zig linker is 0.17.0-dev.1422+e863bf3be and its wrapper keeps the Windows target at `windows.win7`.
- Runtime: the existing local VMware Windows 7 SP1 VM, OS version 6.1.7601. No Windows 10/11 VM is needed for this build or test.
- Both native smoke executables passed on Win7. The raster test confirmed Skia 88.1, HarfBuzz 8.3.1 and pixel/text operations; the ANGLE test initialized EGL successfully.
- The final published Avalonia EXE passed **five consecutive** runs. Each emitted `STATICLINK_SMOKE_READY=opengl;BACKEND=OpenGL` and exited with code 0. A sixth manual run kept the rendered window open.
- The final EXE SHA256 was also computed inside Win7 and matched the macOS build artifact:

```text
1a91d72396d526fdf2ed13baac142ceb80a825966be21aeea28bdc0af1798ea4
```

An earlier diagnostic candidate had one run exit -1 without a rendered-frame marker; the application-error event query returned no matching events. The earlier log is retained separately. The fresh-feed final build passed all five runs above; longer-duration/application feature testing has not been performed.

## Evidence

Under `artifacts/win7-fix/`:

- `publish.log`, `publish.binlog`: complete successful macOS AotAnywhere publish.
- `feed/`: local package candidate with the rebuilt x64 payload and updated targets.
- `runtime-validation.json`: versions, tested EXE hash, and result.
- `win7-native-results.txt`, `win7-avalonia-results.txt`: real guest execution logs.
- `win7-avalonia-earlier-results.txt`: earlier diagnostic log, including the unsuccessful run.
- `pe-imports.txt`: final PE import table.
- `win7-running.png`: rendered final app on the guest desktop.
- `Avalonia11-Win7-x64.zip`: final EXE, instructions, hash and validation metadata.

The generated consumer is `artifacts/win7-fix/app/AvaloniaStaticLinkSmoke.csproj`; its SDK reference is `<Sdk Name="StuDev.AotAnywhere" Version="1.1.0" />`. The final command, from the repository root, is:

```sh
PATH="$PWD/artifacts/win7-fix/host-tools:/usr/local/opt/llvm/bin:$PATH" \
NUGET_PACKAGES="$PWD/artifacts/win7-fix/nuget-cache" \
dotnet publish artifacts/win7-fix/app/AvaloniaStaticLinkSmoke.csproj \
  -c Release -r win-x64 \
  --configfile artifacts/win7-fix/app/NuGet.config \
  -p:UseExternalZig=true -p:RuntimeFrameworkVersion=10.0.11 \
  -p:PublishDir="$PWD/artifacts/win7-fix/publish/" \
  -bl:artifacts/win7-fix/publish.binlog
```

## Regression check and scope

```sh
python3 scripts/check-windows7-imports.py \
  artifacts/win7-fix/publish/AvaloniaStaticLinkSmoke.exe
```

The check rejects the old EXE and accepts the fixed one. It checks the known Win8 imports involved in this regression; it is not a complete API compatibility database. The final EXE still imports UCRT, already installed in this test VM. This validates the tested Avalonia 11 x64 configuration, not every Win7 installation, Avalonia feature, architecture or the Avalonia 12 line. Official .NET support policy is unchanged.

## Windows x86 follow-up

The x86 build also passed five consecutive rendered-frame runs on the existing **Windows 7 SP1 x64 VM under WoW64**. This is a real PE32/Intel 80386 binary; a native 32-bit Windows 7 OS was not tested. The native raster and EGL initialization smoke executables also passed on that guest.

- Same official Avalonia 11.3.22 / SkiaSharp 2.88.9 / HarfBuzzSharp 8.3.1.1 sources.
- Native target: `x86-windows.win7-gnu`, pinned Zig 0.14.1; 1,232 managed-ABI stdcall adapters generated and x86 unwind SafeSEH metadata applied.
- Consumer: macOS, .NET SDK 10.0.401 / runtime 10.0.11. AotAnywhere 1.1.0 provides the cross-compilation frontend. Its Windows MinGW cross-link task does not support x86 and is disabled for this build, using `-p:_AotAnywhereWindowsCross=false -p:IlcUseEnvironmentalTools=true`.
- Link: LLD 23.1.0 with official Microsoft CRT 14.44 and SDK 10.0.26100 x86 libraries downloaded/verified by xwin. No custom replacement SEH/math helper implementation is used. Only the local Win7 VM was used; no newer Windows VM was started for the x86 work.
- Final `dotnet publish` succeeded. LNK4099 messages concern omitted Microsoft CRT debug PDBs; they do not prevent linking or execution.
- All five runs emitted `STATICLINK_SMOKE_READY=opengl;BACKEND=OpenGL` and exited 0. Guest-side SHA256 matched the published EXE:

```text
88ee1f95bf6e98201b74f71d6fa349ce0aa01f9367c53cd52213585a4d5a16c4
```

Evidence and runnable ZIP are under `artifacts/win7-x86/`: `build.log`, `finish-build.log`, `publish.log`, `publish.binlog`, `win7-native-results.txt`, `win7-avalonia-results.txt`, `runtime-validation.json`, `pe-imports.txt`, and `Avalonia11-Win7-x86.zip`. The consumer project in `app/` records the CRT/SDK library search directories and removes the unused Zig target argument for the direct MSVC-compatible LLD link. The known Win8-import regression guard accepts all three final x86 executables.

The tested guest already has the required 32-bit UCRT and VCRUNTIME140 DLLs. The ZIP does not bundle these system/runtime components. This local candidate has not been uploaded to NuGet.

## Saved repository evidence

Compact copies of the final x64/x86 validation reports and native/application guest logs are committed under `build/windows7-validation/`. Full build outputs and the runnable ZIPs remain in the local artifact directories above.

Handoff: changes are on `skiasharp2` (renamed from `fix/windows7-native-compat`). No NuGet upload or workflow dispatch was requested. Both daily workflows are temporarily disabled at the user's request; restore scheduling only when work resumes.
