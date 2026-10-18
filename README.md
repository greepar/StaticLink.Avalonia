# StaticLink.Avalonia — avalonia-native

Builds the separate macOS `StaticLink.Avalonia.Native` static library.

- Match the package version to your application's Avalonia version.
- Linux Zig builds target `osx-x64` and `osx-arm64`; NativeAOT smoke checks run on matching macOS hosts.
- The schedule checks Avalonia 11/12 and currently uploads validated Actions artifacts; NuGet publication is controlled separately.

Select this branch for manual Actions runs. See the [project homepage](https://github.com/greepar/StaticLink.Avalonia) for package selection and usage.
