# StaticLink.Avalonia

[English](README.md) | [简体中文](README.zh-CN.md)

为 Avalonia 提供静态原生库，用于将应用发布为单文件 NativeAOT 可执行文件。

## 安装

根据应用使用的 Avalonia 和 SkiaSharp 主版本，选择匹配的静态图形库包。

| Avalonia 版本 | SkiaSharp 版本 | `StaticLink.Avalonia` 版本 |
| --- | --- | --- |
| 11 | 2.88.9 | `2.88.9-7151.10` |
| 11 | 3.119.4 | `3.119.4-7922.1` |
| 12 | 3.119.4 | `3.119.4-7922.1` |
| 12 | 4.150.1 | `4.150.1-7922.1` |

示例：

```xml
<ItemGroup>
  <PackageReference Include="Avalonia" Version="12.1.0" />
  <PackageReference Include="StaticLink.Avalonia" Version="4.150.1-7922.1" />
</ItemGroup>
```

### macOS

在 macOS 上，还需要引用 `StaticLink.Avalonia.Native`。该包包含 `libAvaloniaNative.a`，因此其版本必须与应用使用的 Avalonia 版本匹配。

```xml
<!-- Avalonia 11.3.14 -->
<PackageReference Include="StaticLink.Avalonia.Native" Version="11.3.14.1" />

<!-- Avalonia 12.1.0 -->
<PackageReference Include="StaticLink.Avalonia.Native" Version="12.1.0.1" />
```

仅添加与所用 Avalonia 版本匹配的那一项 `StaticLink.Avalonia.Native` 引用。

在 macOS 上，只有搭配 SkiaSharp 3 或 4 的 Avalonia 12 才支持 Metal。使用 Avalonia 11 的完全静态链接应用必须采用 OpenGL 或软件渲染，因为其 Metal 渲染路径会动态加载 `libSkiaSharp`。

## 发布

```bash
dotnet publish -c Release -r win-x64 -p:PublishAot=true
```

请根据目标平台选择所需的运行时标识符（RID），例如 `win-x86`、`linux-x64`、`linux-arm64`、`osx-arm64` 或 `osx-x64`。

## 原生库包自动化

`.github/workflows/daily-avalonia-native.yml` 每天运行，检查 NuGet.org 上 Avalonia 11 和 12 的最新稳定版本。如果没有匹配的成功构建 Actions 产物，它会触发 `avalonia-native` 分支上的 `.github/workflows/nuget-avalonia-native.yml`，构建并验证包。这些每日任务仅生成 Actions 产物，不会发布到 NuGet。

原生库包构建工作流会从对应的 Avalonia 源码标签构建两种 macOS 架构的包，并运行 NativeAOT 冒烟测试。NuGet 发布使用 NuGet Trusted Publishing；手动运行工作流时，必须通过 `publish_to_nuget` 输入参数显式启用发布。
