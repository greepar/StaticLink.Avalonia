using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using Avalonia.Threading;

namespace AvaloniaStaticLinkSmoke;

public sealed partial class App : Application
{
    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            var renderer = Environment.GetEnvironmentVariable("STATICLINK_MAC_RENDERER") ?? "opengl";
            var autoClose = Environment.GetEnvironmentVariable("STATICLINK_SMOKE_AUTOCLOSE") == "1";
            desktop.MainWindow = new MainWindow(autoClose ? CompleteSmoke : null);

            void CompleteSmoke(string backend)
            {
                Dispatcher.UIThread.Post(() =>
                {
                    if (!renderer.Equals("metal", StringComparison.OrdinalIgnoreCase) ||
                        backend.Equals("Metal", StringComparison.OrdinalIgnoreCase))
                    {
                        Console.WriteLine($"STATICLINK_SMOKE_READY={renderer};BACKEND={backend}");
                    }
                    else
                    {
                        Console.Error.WriteLine($"Expected the Metal renderer, but the active Skia backend was {backend}.");
                        Environment.ExitCode = 1;
                    }

                    desktop.MainWindow?.Close();
                });
            }
        }

        base.OnFrameworkInitializationCompleted();
    }
}
