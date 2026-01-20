# WordPress Backup Export CLI Tool

A command-line and web-based tool for automating WordPress site backups and migrations to Rocket.net.

## Key Features

- **Automated Export**: Logs in and generates All-in-One WP Migration backups automatically.
- **Rocket.net Integration**: Creates destination sites and sets up SSH keys via API.
- **Remote Restoration**: Downloads and restores backups on Rocket.net using `rmig`.
- **Modern Web UI**: A beautiful, glassmorphic interface for managing migrations without the CLI.

## Web User Interface (Recommended)

![Migration Assistant UI](/Users/andrecorrea/.gemini/antigravity/brain/5c6a45c1-841d-4698-bcf0-1797fb314aa6/migration_assistant_ui_1768921663513.png)

The easiest way to use this tool is via the built-in Web UI.

1. **Install Dependencies**:
   ```bash
   python3 -m pip install fastapi uvicorn requests playwright
   python3 -m playwright install chromium
   ```
2. **Start the Server**:
   ```bash
   python3 app.py
   ```
3. **Access the UI**: Open **[http://localhost:8000](http://localhost:8000)** in your browser.

## CLI Usage (Advanced)

- Python 3.6+
- Playwright for Python
  - Install with: `pip install playwright`
  - Install browsers: `playwright install chromium`
- Requests: `pip install requests`

## Usage

Basic usage:

```bash
python cli-export-aio.py --admin-url YOUR_WP_ADMIN_URL --username YOUR_USERNAME --password 'YOUR_PASSWORD'
```

Example:

```bash
python cli-export-aio.py --admin-url https://rocket.net/wp-admin/ --username hello@rocket.net --password 'pass'
```

### Rocket.net Migration (Optional)

You can automatically migrate the backup to Rocket.net:

```bash
python exportaiocli.py \
  --admin-url https://example.com/wp-admin \
  --username admin \
  --password 'pass' \
  --rocket-token 'YOUR_ROCKET_API_TOKEN' \
  --rocket-name 'new-site-slug' \
  --rocket-location 21
```

### Parameters

#### WordPress source:
- `--admin-url`: Your WordPress admin URL (e.g., https://example.com/wp-admin)
- `--username`: WordPress admin username
- `--password`: WordPress admin password
- `--visual`: (Optional) Run in visual mode to see the browser automation

#### Rocket.net destination (Optional):
- `--rocket-token`: Your Rocket.net API Token (can also be set via `ROCKET_NET_TOKEN` environment variable)
- `--rocket-name`: The slug/name for the new site on Rocket.net
- `--rocket-location`: Location ID (e.g., 12 for US Central, 21 for US East)
- `--rocket-label`: Label for the site in Rocket dashboard
- `--rocket-admin-user`: Admin username for the new site (default: admin)
- `--rocket-admin-pass`: Admin password for the new site (randomly generated if omitted)
- `--ssh-key-path`: Path to your SSH public key (default: `~/.ssh/id_ed25519.pub` or `~/.ssh/id_rsa.pub`)

## Important Notes

- **Web Application Firewalls (WAF)**: Login pages often implement WAF protection which may block automated login attempts. If you experience issues, try:
  - Using the `--visual` flag to see what's happening
  - Temporarily disabling WAF or security plugins if possible
  - Implementing a delay between actions by modifying the script

- The script provides a `wget` command for downloading the backup file once the export is complete.

- For large sites, the export process may take several minutes.

## Troubleshooting

- If the script can't find the All-in-One WP Migration plugin, it will attempt to proceed to the export page directly.
- In visual mode (using the `--visual` flag), you can observe the automation process and press Enter to close the browser when finished.
- If login fails, check your credentials and ensure that your site doesn't have additional security measures that prevent automated logins.

## Build from Source

If you need to build the executable yourself:

1. Clone this repository
2. Install the dependencies: `pip install playwright pyinstaller`
3. Install Playwright browser: `python -m playwright install chromium`
4. Run the build script: `python build_executable.py`

The resulting executable will be in the `dist` directory.

## Troubleshooting

- **File permissions**: Make sure the executable has proper execute permissions (`chmod +x cli-export-aio`)
- **Browser issues**: The tool uses a headless browser; make sure your CloudLinux environment supports this
- **Memory requirements**: The executable requires approximately 200-300MB of RAM to run properly
- **Disk space**: Ensure you have enough disk space for both the executable (~500MB) and the backup file

## Notes for CloudLinux Environments

- The tool creates temporary files during operation, so ensure you have at least 1GB of free disk space
- If your hosting provider limits process execution time, you might need to adjust your PHP settings or contact your hosting provider
- The executable includes its own browser binaries, so it doesn't depend on system libraries

## License

This tool is provided under the MIT License. See the LICENSE file for details.
