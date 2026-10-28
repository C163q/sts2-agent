using System.Collections.Concurrent;
using System.Text.Json;

namespace Sts2Agent;

internal sealed record Request(string Id, string Operation, string? ExpectedState);

internal sealed class WorkItem(Request request)
{
    public Request Request { get; } = request;
    public DateTime Deadline { get; } = DateTime.UtcNow.AddSeconds(30);
    public TaskCompletionSource<string> Completion { get; } =
        new(TaskCreationOptions.RunContinuationsAsynchronously);
}

internal sealed class FileMailbox(string directory)
{
    public ConcurrentQueue<WorkItem> Queue { get; } = new();

    public async Task Run(CancellationToken cancellation)
    {
        string requests = Path.Combine(directory, "requests");
        string responses = Path.Combine(directory, "responses");
        Directory.CreateDirectory(requests);
        Directory.CreateDirectory(responses);
        while (!cancellation.IsCancellationRequested)
        {
            foreach (string path in Directory.EnumerateFiles(requests, "*.json").Order())
            {
                string id = Path.GetFileNameWithoutExtension(path);
                if (!Guid.TryParseExact(id, "N", out _))
                    continue;
                string responsePath = Path.Combine(responses, id + ".json");
                if (File.Exists(responsePath))
                {
                    File.Delete(path);
                    continue;
                }

                string response;
                try
                {
                    if (new FileInfo(path).Length > 65536)
                        throw new JsonException("Request exceeds 64 KiB.");
                    using JsonDocument document = JsonDocument.Parse(await File.ReadAllTextAsync(path, cancellation));
                    JsonElement root = document.RootElement;
                    string operation = root.GetProperty("operation").GetString()
                        ?? throw new JsonException("Missing operation.");
                    if (root.GetProperty("id").GetString() != id)
                        throw new JsonException("Request id must match filename.");
                    string? expected = root.TryGetProperty("expected_state", out JsonElement token)
                        ? token.GetString() : null;
                    WorkItem work = new(new Request(id, operation, expected));
                    Queue.Enqueue(work);
                    try
                    {
                        response = await work.Completion.Task.WaitAsync(TimeSpan.FromSeconds(35), cancellation);
                    }
                    catch (TimeoutException)
                    {
                        response = Error(id, "timeout", "Game did not respond; execution outcome is unknown.");
                        work.Completion.TrySetResult(response);
                    }
                }
                catch (Exception error) when (error is JsonException or KeyNotFoundException or InvalidOperationException)
                {
                    response = Error(id, "invalid_request", error.Message);
                }
                string temporary = responsePath + ".tmp";
                await File.WriteAllTextAsync(temporary, response, cancellation);
                File.Move(temporary, responsePath, overwrite: true);
                File.Delete(path);
            }
            await Task.Delay(20, cancellation);
        }
    }

    public static string Error(string id, string code, string message) =>
        JsonSerializer.Serialize(new { id, ok = false, error = new { code, message } });
}
