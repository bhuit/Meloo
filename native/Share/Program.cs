using Windows.ApplicationModel.DataTransfer;
using Windows.Storage;
using WinRT;

internal static class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        if (args.Length == 0) return;
        if (args[0] == "--check") return;
        ApplicationConfiguration.Initialize();
        var form = new Form { Text = "Zeste · Partager", Width = 420, Height = 150, StartPosition = FormStartPosition.CenterScreen, TopMost = true };
        var label = new Label { Text = "Choisis une destination dans le volet de partage Windows.", Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleCenter };
        form.Controls.Add(label);
        DataTransferManager? manager = null;
        form.Shown += (_, _) =>
        {
            try
            {
                manager = DataTransferManagerInterop.GetForWindow(form.Handle);
                manager.DataRequested += async (_, ev) =>
                {
                    var deferral = ev.Request.GetDeferral();
                    try
                    {
                        var items = new List<IStorageItem>();
                        foreach (var path in args)
                        {
                            if (Directory.Exists(path)) items.Add(await StorageFolder.GetFolderFromPathAsync(Path.GetFullPath(path)));
                            else items.Add(await StorageFile.GetFileFromPathAsync(Path.GetFullPath(path)));
                        }
                        ev.Request.Data.Properties.Title = items.Count == 1 ? items[0].Name : $"{items.Count} fichiers";
                        ev.Request.Data.SetStorageItems(items);
                    }
                    catch (Exception ex) { ev.Request.FailWithDisplayText(ex.Message); }
                    finally { deferral.Complete(); }
                };
                DataTransferManagerInterop.ShowShareUIForWindow(form.Handle);
            }
            catch (Exception ex) { label.Text = "Le partage Windows n’a pas pu s’ouvrir : " + ex.Message; }
        };
        Application.Run(form);
    }
}
