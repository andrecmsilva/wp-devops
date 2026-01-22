#!/usr/bin/env python3

import os
import time
import argparse
import asyncio
import sys
import requests
import subprocess
import json
import secrets
import string
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def log_info(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

# Common modern User-Agent to use across requests and Playwright
MODERN_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class NetworkClient:
    """A robust network client with retries and browser-like headers."""
    
    @staticmethod
    def get_session():
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Set browser-like headers
        session.headers.update({
            "User-Agent": MODERN_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        })
        
        return session

# If running as PyInstaller bundle, set browser path to the bundled browser
def set_playwright_browser_path():
    # Check if running as bundled executable
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # We're running as PyInstaller bundle
        bundle_dir = sys._MEIPASS
        browser_path = os.path.join(bundle_dir, 'playwright', '.local-browsers')
        if os.path.exists(browser_path):
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browser_path
            log_info(f"Using bundled browser at: {browser_path}")
            return True
    return False

async def setup_browser(headless=True):
    """Set up and return a Playwright browser with appropriate options."""
    # Set browser path if running as bundled executable
    set_playwright_browser_path()
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=headless,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-extensions",
            "--disable-infobars",
            "--disable-notifications",
            "--disable-popup-blocking",
            "--disable-blink-features=AutomationControlled" # Hide automation flag
        ]
    )
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=MODERN_USER_AGENT
    )
    page = await context.new_page()
    page.set_default_timeout(30000)  # 30 seconds default timeout
    return playwright, browser, context, page

class RocketAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://api.rocket.net/v1"
        self.session = NetworkClient.get_session()
        # Authorization header is specific to this API, so we add it to the generic browser headers
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json" # API expects json
        })

    def create_site(self, name, location, admin_user, admin_pass, admin_email, label):
        url = f"{self.base_url}/sites"
        payload = {
            "multisite": False,
            "name": name,
            "location": location,
            "admin_username": admin_user,
            "admin_password": admin_pass,
            "admin_email": admin_email,
            "label": label,
            "static_site": False,
            "php_version": "8.3"
        }
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def get_site_info(self, site_id):
        url = f"{self.base_url}/sites/{site_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def add_ssh_key(self, site_id, name, public_key):
        url = f"{self.base_url}/sites/{site_id}/ssh/keys"
        payload = {
            "name": name,
            "key": public_key
        }
        response = self.session.post(url, json=payload)
        # If key already exists, we might get an error, but we can usually continue
        if response.status_code != 200 and response.status_code != 201:
            log_info(f"Warning: SSH key addition returned {response.status_code}: {response.text}")
        return response.json()

    def authorize_ssh_key(self, site_id, name):
        url = f"{self.base_url}/sites/{site_id}/ssh/keys/authorize"
        payload = { "name": name }
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def enable_ssh_access(self, site_id):
        url = f"{self.base_url}/sites/{site_id}/settings"
        payload = { "ssh_access": 1 }
        response = self.session.patch(url, json=payload)
        response.raise_for_status()
        return response.json()

def get_ssh_key(key_path=None):
    if not key_path:
        key_path = os.path.expanduser("~/.ssh/id_ed25519.pub")
        if not os.path.exists(key_path):
            key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
    
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            return f.read().strip(), os.path.basename(key_path).split('.')[0]
    return None, None

async def run_remote_migration(sftp_user, host_ip, backup_url):
    log_info(f"Starting remote migration on {host_ip} for user {sftp_user}...")
    
    # Building the remote command
    # Step 9 & 10 from instructions
    remote_cmd = (
        f"wget -c '{backup_url}' && "
        f"wget -c http://wpscripts.onrocket.cloud/assets/rmig --header='User-Agent: RocketScripts' && "
        f"bash rmig restoreaio latest"
    )
    
    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        f"{sftp_user}@{host_ip}",
        remote_cmd
    ]
    
    print(f"Executing: {' '.join(ssh_cmd)}")
    process = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    for line in process.stdout:
        log_info(f"[SSH] {line.strip()}")
    
    process.wait()
    if process.returncode == 0:
        log_info("Remote migration completed successfully!")
        return True
    else:
        log_info(f"Remote migration failed with return code {process.returncode}")
        return False

async def wait_for_page_load(page, timeout=30):
    """Wait for page to be fully loaded."""
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=timeout * 1000)
        await page.wait_for_load_state("networkidle", timeout=timeout * 1000)
        return True
    except PlaywrightTimeoutError:
        return False

async def login_to_wordpress(page, admin_url, username, password):
    """Login to WordPress admin."""
    log_info(f"Logging into {admin_url}...")
    
    await page.goto(admin_url)
    
    try:
        # Wait for the login form to load
        await page.wait_for_selector("#user_login", timeout=10000)
        
        # Fill in login credentials
        await page.fill("#user_login", username)
        await page.fill("#user_pass", password)
        await page.click("#wp-submit")
        
        # Wait for dashboard to load
        await page.wait_for_selector("#wpadminbar", timeout=10000)
        log_info("Login successful!")
        
        # Always ensure we have the correct WordPress admin URL format
        if '/wp-admin' not in admin_url:
            # Extract the base URL (domain)
            if '//' in admin_url:
                base_url = admin_url.split('//')[0] + '//' + admin_url.split('//')[1].split('/')[0]
            else:
                base_url = admin_url.split('/')[0]
            new_admin_url = f"{base_url}/wp-admin"
            log_info(f"Switching to correct admin URL: {new_admin_url}")
            return new_admin_url
        return admin_url
    
    except PlaywrightTimeoutError:
        log_info("Error: Login page did not load or login failed")
        return None

async def get_base_domain(admin_url):
    """Extract base domain from admin URL."""
    if '//' in admin_url:
        base_domain = admin_url.split('//')[0] + '//' + admin_url.split('//')[1].split('/')[0]
    else:
        base_domain = admin_url.split('/')[0]
    return base_domain

async def install_migration_plugin(page, admin_url):
    """Install the All-in-One WP Migration plugin using direct search URL."""
    log_info("Installing All-in-One WP Migration plugin...")
    
    # Get base domain
    base_domain = await get_base_domain(admin_url)
    
    # Use the direct search URL as requested
    search_url = f"{base_domain}/wp-admin/plugin-install.php?s=all-in-one%2520WP%2520Migration%2520and%2520Backup&tab=search&type=term"
    log_info(f"Accessing direct plugin search page: {search_url}")
    await page.goto(search_url)
    
    # Wait for page load
    if not await wait_for_page_load(page):
        log_info("Warning: Plugin search page load timeout, continuing anyway...")
    
    try:
        # Try to find the plugin card
        log_info("Looking for plugin card...")
        try:
            # Using various selectors to find the plugin card
            plugin_card = await page.wait_for_selector("div.plugin-card.plugin-card-all-in-one-wp-migration", timeout=10000)
            print("Found plugin card using exact class structure")
        except PlaywrightTimeoutError:
            try:
                plugin_card = await page.wait_for_selector("//h3[contains(.,'All-in-One WP Migration')]/ancestor::div[contains(@class,'plugin-card')]", timeout=10000)
                print("Found plugin card by title content")
            except PlaywrightTimeoutError:
                try:
                    plugin_card = await page.wait_for_selector("div[data-slug='all-in-one-wp-migration']", timeout=10000)
                    print("Found plugin card by data-slug attribute")
                except PlaywrightTimeoutError:
                    print("Falling back to first plugin card in search results...")
                    plugin_cards = await page.query_selector_all("div.plugin-card")
                    if plugin_cards:
                        plugin_card = plugin_cards[0]
                        print("Using first plugin card from search results")
                    else:
                        log_info("No plugin cards found in search results")
                        # Instead of failing, we'll try to proceed to the export page directly
                        return False
        
        if plugin_card:
            log_info("Found plugin card, attempting to find installation/activation button...")
            
            # Look for any action button on the plugin card
            buttons = []
            try:
                buttons = await plugin_card.query_selector_all("a.button")
            except Exception as e:
                log_info(f"Error finding buttons: {str(e)}")
            
            if buttons:
                action_button = buttons[0]  # Use the first button found
                button_text = await action_button.text_content()
                log_info(f"Found button with text: {button_text}")
                
                # Click the button regardless of its text - it could be Install Now, Activate, or already activated
                log_info(f"Clicking button: {button_text}")
                await action_button.click()
                
                # Wait for potential activation button after installation
                try:
                    activate_button = await page.wait_for_selector("a.button.activate-now:has-text('Activate')", timeout=120000)
                    log_info("Installation complete, activating plugin...")
                    await activate_button.click()
                    await page.wait_for_selector("#wpadminbar", timeout=30000)
                    log_info("Plugin activated successfully!")
                except PlaywrightTimeoutError:
                    log_info("No activation button found, plugin may already be activated")
                    
                # Regardless of what happened, we'll proceed to check the export page
                return True
            else:
                log_info("No action buttons found on plugin card")
                # We'll try to proceed to the export page anyway
                return False
        else:
            log_info("Failed to find plugin card")
            return False
            
    except Exception as e:
        log_info(f"Unexpected error during plugin installation: {str(e)}")
        # Let's not fail here, try to proceed to export page
        return False

async def check_export_page_exists(page, admin_url):
    """Check if the export page exists, which would indicate the plugin is already installed."""
    base_domain = await get_base_domain(admin_url)
    export_url = f"{base_domain}/wp-admin/admin.php?page=ai1wm_export"
    
    log_info(f"Checking if export page exists: {export_url}")
    await page.goto(export_url)
    
    try:
        # Wait for the export dropdown button to be present
        export_button = await page.wait_for_selector("div.ai1wm-button-export", timeout=10000)
        if export_button:
            log_info("Export page exists! Plugin appears to be installed and activated.")
            return True
    except PlaywrightTimeoutError:
        log_info("Export page does not exist or is not accessible.")
        return False
    except Exception as e:
        log_info(f"Error checking export page: {str(e)}")
        return False
    
    return False

async def get_backup_url(page, admin_url):
    """Get the backup file URL using All-in-One WP Migration plugin."""
    log_info("Getting backup file URL...")
    
    # Ensure we're using the correct WordPress admin URL for export
    base_domain = await get_base_domain(admin_url)
    export_url = f"{base_domain}/wp-admin/admin.php?page=ai1wm_export"
    log_info(f"Accessing export page: {export_url}")
    await page.goto(export_url)
    
    try:
        # Wait for the export dropdown button to be present
        log_info("Waiting for export dropdown button...")
        export_button = await page.wait_for_selector("div.ai1wm-button-export", timeout=10000)
        
        # Click the export dropdown button
        log_info("Clicking export dropdown button...")
        await export_button.click()
        
        # Wait for and click the File option in the dropdown
        log_info("Selecting File export option...")
        file_option = await page.wait_for_selector("#ai1wm-export-file", timeout=10000)
        await file_option.click()
        
        # Wait for export to complete and find the download button
        log_info("Waiting for export to complete...")
        download_button = await page.wait_for_selector("a.ai1wm-button-green.ai1wm-emphasize.ai1wm-button-download", timeout=300000)  # 5-minute timeout
        
        # Get the download link
        download_link = await download_button.get_attribute("href")
        log_info(f"Export completed! Download URL: {download_link}")
        return download_link
    
    except PlaywrightTimeoutError as e:
        log_info(f"Error: Export timed out or failed - {str(e)}")
        return None
    except Exception as e:
        log_info(f"Unexpected error during export: {str(e)}")
        return None

async def main_async(visual_mode=False):
    """Main async function."""
    parser = argparse.ArgumentParser(description="Get WordPress backup URL using All-in-One WP Migration")
    parser.add_argument("--admin-url", required=True, help="WordPress admin URL (e.g., https://example.com/wp-admin)")
    parser.add_argument("--username", required=True, help="WordPress admin username")
    parser.add_argument("--password", required=True, help="WordPress admin password")
    parser.add_argument("--visual", action="store_true", help="Run in visual mode (show browser window)")
    
    # Rocket.net arguments
    parser.add_argument("--rocket-token", help="Rocket.net API Token")
    parser.add_argument("--rocket-name", help="New site name for Rocket.net")
    parser.add_argument("--rocket-location", type=int, default=12, help="Rocket.net location ID (default: 12 - US Central)")
    parser.add_argument("--rocket-label", help="Rocket.net site label")
    parser.add_argument("--rocket-admin-user", default="admin", help="Rocket.net admin username")
    parser.add_argument("--rocket-admin-pass", help="Rocket.net admin password (random if not provided)")
    parser.add_argument("--rocket-admin-email", help="Rocket.net admin email")
    parser.add_argument("--ssh-key-path", help="Path to your local SSH public key")
    
    args = parser.parse_args()
    
    # Initialize timing statistics
    start_time = time.time()
    stats = {
        'login': 0,
        'plugin_installation': 0,
        'export': 0,
        'total': 0
    }
    
    # Use visual mode if specified in args or if visual_mode parameter is True
    headless = not (args.visual or visual_mode)
    headless = not (args.visual or visual_mode)
    if not headless:
        log_info("Running in visual mode - browser window will be visible")
    
    playwright, browser, context, page = await setup_browser(headless=headless)
    
    try:
        # Step 1: Login to WordPress and get the correct admin URL
        login_start = time.time()
        admin_url = await login_to_wordpress(page, args.admin_url, args.username, args.password)
        stats['login'] = time.time() - login_start
        if not admin_url:
            log_info("Exiting due to login failure")
            return
        
        # Step 2: First check if the export page already exists
        plugin_start = time.time()
        export_page_exists = await check_export_page_exists(page, admin_url)
        
        if not export_page_exists:
            # Try to install the plugin if the export page doesn't exist
            log_info("Export page not found. Attempting to install the plugin...")
            await install_migration_plugin(page, admin_url)
            
            # Double-check if the export page exists after installation attempt
            export_page_exists = await check_export_page_exists(page, admin_url)
            if not export_page_exists:
                log_info("Failed to access export page after installation attempt. Exiting.")
                return
        
        stats['plugin_installation'] = time.time() - plugin_start
        
        # Step 3: Get backup URL
        export_start = time.time()
        backup_url = await get_backup_url(page, admin_url)
        stats['export'] = time.time() - export_start
        
        if backup_url:
            log_info("\nTo download the backup file, use this command:")
            log_info(f"wget -c {backup_url}")
            
            # Check if Rocket.net migration is requested
            rocket_token = args.rocket_token or os.environ.get("ROCKET_NET_TOKEN")
            if rocket_token and args.rocket_name:
                log_info("\n" + "="*50)
                log_info("STARTING ROCKET.NET MIGRATION")
                log_info("="*50)
                
                try:
                    rocket = RocketAPI(rocket_token)
                    
                    # 5. Create site
                    log_info(f"Creating site '{args.rocket_name}' on Rocket.net...")
                    if args.rocket_admin_pass:
                        admin_pass = args.rocket_admin_pass
                    else:
                        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                        admin_pass = ''.join(secrets.choice(alphabet) for i in range(16))
                    
                    admin_email = args.rocket_admin_email or f"admin@{args.rocket_name}.com"
                    
                    site_creation = rocket.create_site(
                        name=args.rocket_name,
                        location=args.rocket_location,
                        admin_user=args.rocket_admin_user,
                        admin_pass=admin_pass,
                        admin_email=admin_email,
                        label=args.rocket_label or args.rocket_name
                    )
                    
                    site_id = site_creation['result']['id']
                    temp_domain = site_creation['result']['domain']
                    log_info(f"Site created! ID: {site_id}, Domain: {temp_domain}")
                    log_info(f"Admin Credentials: {args.rocket_admin_user} / {admin_pass}")
                    
                    # 6. Get site info
                    log_info("Fetching site details (IP and SFTP User)...")
                    # Rocket.net might need a moment to provision
                    time.sleep(5)
                    site_info = rocket.get_site_info(site_id)
                    sftp_user = site_info['result']['sftp_username']
                    host_ip = site_info['result']['ftp_ip_address']
                    log_info(f"SFTP User: {sftp_user}, host IP: {host_ip}")
                    
                    # 7. SSH Key setup
                    pub_key, key_name = get_ssh_key(args.ssh_key_path)
                    pub_key, key_name = get_ssh_key(args.ssh_key_path)
                    if pub_key:
                        log_info(f"Importing SSH key '{key_name}'...")
                        rocket.add_ssh_key(site_id, key_name, pub_key)
                        log_info(f"Authorizing SSH key '{key_name}'...")
                        rocket.authorize_ssh_key(site_id, key_name)
                        log_info("Enabling SSH access...")
                        rocket.enable_ssh_access(site_id)
                        
                        # Wait a bit for SSH access to be active
                        log_info("Waiting for SSH to become active (10s)...")
                        time.sleep(10)
                        
                        # 8, 9, 10. Run remote migration
                        await run_remote_migration(sftp_user, host_ip, backup_url)
                    else:
                        log_info("Warning: No SSH public key found. Skipping remote migration steps.")
                        log_info(f"You can manually migration by connecting to {sftp_user}@{host_ip}")
                
                except Exception as e:
                    log_info(f"Error during Rocket.net migration: {str(e)}")
        else:
            log_info("Failed to get backup URL")
        
    finally:
        # In visual mode, wait for user to press Enter before closing
        if not headless:
            input("\nPress Enter to close the browser...")
        
        await context.close()
        await browser.close()
        await playwright.stop()
    
    # Calculate total time and display statistics
    stats['total'] = time.time() - start_time
    log_info("\n" + "="*50)
    log_info("EXECUTION STATISTICS")
    log_info("="*50)
    print(f"Login time: {stats['login']:.2f} seconds")
    print(f"Plugin installation time: {stats['plugin_installation']:.2f} seconds")
    print(f"Export time: {stats['export']:.2f} seconds")
    print("-"*50)
    print(f"Total execution time: {stats['total']:.2f} seconds")
    print("="*50 + "\n")

def main():
    """Main function that runs the async main function."""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
