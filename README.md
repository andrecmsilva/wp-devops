# WordPress Backup Export CLI Tool

A command-line tool for automating WordPress site backups using the All-in-One WP Migration plugin.

## What it does

This script automates the process of:
1. Logging into your WordPress admin dashboard
2. Installing the All-in-One WP Migration plugin (if not already installed)
3. Initiating a site export/backup
4. Providing a downloadable URL for the backup file

## Requirements

- Python 3.6+
- Playwright for Python
  - Install with: `pip install playwright`
  - Install browsers: `playwright install chromium`

## Usage

Basic usage:

```bash
python cli-export-aio.py --admin-url YOUR_WP_ADMIN_URL --username YOUR_USERNAME --password 'YOUR_PASSWORD'
```

Example:

```bash
python cli-export-aio.py --admin-url https://rocket.net/wp-admin/ --username hello@rocket.net --password 'pass'
```

### Parameters

- `--admin-url`: Your WordPress admin URL (e.g., https://example.com/wp-admin)
- `--username`: WordPress admin username
- `--password`: WordPress admin password
- `--visual`: (Optional) Run in visual mode to see the browser automation

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
