# a4_printer_webserver

A single-printer web interface built with Flask and native WebSockets. It uses
[`a4-printer-interface`](https://pypi.org/project/a4-printer-interface/) to
discover the printer, monitor its activity, and submit PDF documents or images.

## Installation

Python 3.10 or newer is required. The target printer must already be configured
in the operating system.

```powershell
python -m pip install a4_printer_webserver
```

First, list the available printers and their UUIDs:

```powershell
python -m a4_printer_interface
```

Then start the website:

```powershell
python -m a4_printer_webserver `
  --uuid "printer uuid" `
  --password "your password"
```

The server listens on <http://127.0.0.1:5000> by default, and the default page
title is `Printer Website`. To use a custom title:

```powershell
python -m a4_printer_webserver `
  --uuid "8fd0d51f-12c8-5b50-a2f1-4f64641ae77c" `
  --password "your password" `
  --title "New Title"
```

Both `--uuid` and `--password` are required. An empty password is rejected.
The following options are also available:

- `--host 127.0.0.1`: Address on which the server listens. Use `0.0.0.0` to
  allow access from the local network.
- `--port 5000`: TCP port on which the server listens.
- `--data-dir printer_data`: Directory for uploaded files, the SQLite queue,
  and print history.
- `--max-upload-mb 100`: Maximum size of one uploaded file, in MiB.
- `--auto-delete DAYS`: Automatically delete submitted document files after a
  positive number of days. Automatic deletion is disabled when this option is
  omitted.

When exposing the service to a local network or the internet, place it behind
an HTTPS-enabled reverse proxy. Passwords and documents should not cross an
untrusted network over plain HTTP.

## Behavior

- Unauthenticated users can only access the login page. They cannot view the
  queue, download previously submitted files, or establish an authenticated
  WebSocket connection.
- Uploading a document does not print it immediately. The user must click
  `Print` before the document enters the queue.
- The `Print test page` button asks for confirmation before adding the built-in
  test page to the queue. It can be canceled until printing starts.
- `Pause printing` prevents queued jobs from starting. It does not interrupt a
  job that is already printing, and the paused state resets when the server
  restarts.
- Documents that have not started printing can be canceled. A document in the
  `printing` state cannot be canceled.
- After the printing library returns successfully, the job is shown as
  `Submitted`. This means that the operating system accepted the job; it does
  not guarantee that the physical pages have finished printing.
- A green light means the printer is idle, yellow means the printer or the
  current submission is busy, and red means that the configured UUID cannot be
  found or the print service status cannot be read.
- While the printer reports that it is busy, the most recently submitted job
  remains in History but is displayed as `Printing`. It returns to `Submitted`
  when the printer becomes idle.
- A submitted document can be deleted manually after confirmation. Manual and
  automatic deletion remove only the stored file; the History entry remains.
  Its Download button is then shown as disabled. Files for jobs currently shown
  as `Printing`, and built-in test-page jobs, do not offer a Delete button.
- The queue and history are stored in SQLite. If the server stops unexpectedly,
  a job that was being submitted is marked as failed and is not printed again
  automatically.

## Tests

```powershell
python -m unittest discover -s tests -v
```
