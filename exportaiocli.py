#!/usr/bin/env python3

import os
import time
import argparse
import asyncio
import sys
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# If running as PyInstaller bundle, set browser path to the bundled browser
def set_playwright_browser_path():
    # Check if running as bundled executable
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # We're running as PyInstaller bundle
        bundle_dir = sys._MEIPASS
        browser_path = os.path.join(bundle_dir, 'playwright', '.local-browsers')
        if os.path.exists(browser_path):
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browser_path
            print(f"Using bundled browser at: {browser_path}")
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
            "--disable-popup-blocking"
        ]
    )
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    page = await context.new_page()
    page.set_default_timeout(30000)  # 30 seconds default timeout
    return playwright, browser, context, page

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
    print(f"Logging into {admin_url}...")
    
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
        print("Login successful!")
        
        # Always ensure we have the correct WordPress admin URL format
        if '/wp-admin' not in admin_url:
            # Extract the base URL (domain)
            if '//' in admin_url:
                base_url = admin_url.split('//')[0] + '//' + admin_url.split('//')[1].split('/')[0]
            else:
                base_url = admin_url.split('/')[0]
            new_admin_url = f"{base_url}/wp-admin"
            print(f"Switching to correct admin URL: {new_admin_url}")
            return new_admin_url
        return admin_url
    
    except PlaywrightTimeoutError:
        print("Error: Login page did not load or login failed")
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
    print("Installing All-in-One WP Migration plugin...")
    
    # Get base domain
    base_domain = await get_base_domain(admin_url)
    
    # Use the direct search URL as requested
    search_url = f"{base_domain}/wp-admin/plugin-install.php?s=all-in-one%2520WP%2520Migration%2520and%2520Backup&tab=search&type=term"
    print(f"Accessing direct plugin search page: {search_url}")
    await page.goto(search_url)
    
    # Wait for page load
    if not await wait_for_page_load(page):
        print("Warning: Plugin search page load timeout, continuing anyway...")
    
    try:
        # Try to find the plugin card
        print("\nLooking for plugin card...")
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
                        print("No plugin cards found in search results")
                        # Instead of failing, we'll try to proceed to the export page directly
                        return False
        
        if plugin_card:
            print("Found plugin card, attempting to find installation/activation button...")
            
            # Look for any action button on the plugin card
            buttons = []
            try:
                buttons = await plugin_card.query_selector_all("a.button")
            except Exception as e:
                print(f"Error finding buttons: {str(e)}")
            
            if buttons:
                action_button = buttons[0]  # Use the first button found
                button_text = await action_button.text_content()
                print(f"Found button with text: {button_text}")
                
                # Click the button regardless of its text - it could be Install Now, Activate, or already activated
                print(f"Clicking button: {button_text}")
                await action_button.click()
                
                # Wait for potential activation button after installation
                try:
                    activate_button = await page.wait_for_selector("a.button.activate-now:has-text('Activate')", timeout=120000)
                    print("Installation complete, activating plugin...")
                    await activate_button.click()
                    await page.wait_for_selector("#wpadminbar", timeout=30000)
                    print("Plugin activated successfully!")
                except PlaywrightTimeoutError:
                    print("No activation button found, plugin may already be activated")
                    
                # Regardless of what happened, we'll proceed to check the export page
                return True
            else:
                print("No action buttons found on plugin card")
                # We'll try to proceed to the export page anyway
                return False
        else:
            print("Failed to find plugin card")
            return False
            
    except Exception as e:
        print(f"Unexpected error during plugin installation: {str(e)}")
        # Let's not fail here, try to proceed to export page
        return False

async def check_export_page_exists(page, admin_url):
    """Check if the export page exists, which would indicate the plugin is already installed."""
    base_domain = await get_base_domain(admin_url)
    export_url = f"{base_domain}/wp-admin/admin.php?page=ai1wm_export"
    
    print(f"Checking if export page exists: {export_url}")
    await page.goto(export_url)
    
    try:
        # Wait for the export dropdown button to be present
        export_button = await page.wait_for_selector("div.ai1wm-button-export", timeout=10000)
        if export_button:
            print("Export page exists! Plugin appears to be installed and activated.")
            return True
    except PlaywrightTimeoutError:
        print("Export page does not exist or is not accessible.")
        return False
    except Exception as e:
        print(f"Error checking export page: {str(e)}")
        return False
    
    return False

async def get_backup_url(page, admin_url):
    """Get the backup file URL using All-in-One WP Migration plugin."""
    print("Getting backup file URL...")
    
    # Ensure we're using the correct WordPress admin URL for export
    base_domain = await get_base_domain(admin_url)
    export_url = f"{base_domain}/wp-admin/admin.php?page=ai1wm_export"
    print(f"Accessing export page: {export_url}")
    await page.goto(export_url)
    
    try:
        # Wait for the export dropdown button to be present
        print("Waiting for export dropdown button...")
        export_button = await page.wait_for_selector("div.ai1wm-button-export", timeout=10000)
        
        # Click the export dropdown button
        print("Clicking export dropdown button...")
        await export_button.click()
        
        # Wait for and click the File option in the dropdown
        print("Selecting File export option...")
        file_option = await page.wait_for_selector("#ai1wm-export-file", timeout=10000)
        await file_option.click()
        
        # Wait for export to complete and find the download button
        print("Waiting for export to complete...")
        download_button = await page.wait_for_selector("a.ai1wm-button-green.ai1wm-emphasize.ai1wm-button-download", timeout=300000)  # 5-minute timeout
        
        # Get the download link
        download_link = await download_button.get_attribute("href")
        print(f"Export completed! Download URL: {download_link}")
        return download_link
    
    except PlaywrightTimeoutError as e:
        print(f"Error: Export timed out or failed - {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error during export: {str(e)}")
        return None

async def main_async(visual_mode=False):
    """Main async function."""
    parser = argparse.ArgumentParser(description="Get WordPress backup URL using All-in-One WP Migration")
    parser.add_argument("--admin-url", required=True, help="WordPress admin URL (e.g., https://example.com/wp-admin)")
    parser.add_argument("--username", required=True, help="WordPress admin username")
    parser.add_argument("--password", required=True, help="WordPress admin password")
    parser.add_argument("--visual", action="store_true", help="Run in visual mode (show browser window)")
    
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
    if not headless:
        print("Running in visual mode - browser window will be visible")
    
    playwright, browser, context, page = await setup_browser(headless=headless)
    
    try:
        # Step 1: Login to WordPress and get the correct admin URL
        login_start = time.time()
        admin_url = await login_to_wordpress(page, args.admin_url, args.username, args.password)
        stats['login'] = time.time() - login_start
        if not admin_url:
            print("Exiting due to login failure")
            return
        
        # Step 2: First check if the export page already exists
        plugin_start = time.time()
        export_page_exists = await check_export_page_exists(page, admin_url)
        
        if not export_page_exists:
            # Try to install the plugin if the export page doesn't exist
            print("Export page not found. Attempting to install the plugin...")
            await install_migration_plugin(page, admin_url)
            
            # Double-check if the export page exists after installation attempt
            export_page_exists = await check_export_page_exists(page, admin_url)
            if not export_page_exists:
                print("Failed to access export page after installation attempt. Exiting.")
                return
        
        stats['plugin_installation'] = time.time() - plugin_start
        
        # Step 3: Get backup URL
        export_start = time.time()
        backup_url = await get_backup_url(page, admin_url)
        stats['export'] = time.time() - export_start
        
        if backup_url:
            print("\nTo download the backup file, use this command:")
            print(f"wget -c {backup_url}")
        else:
            print("Failed to get backup URL")
        
    finally:
        # In visual mode, wait for user to press Enter before closing
        if not headless:
            input("\nPress Enter to close the browser...")
        
        await context.close()
        await browser.close()
        await playwright.stop()
    
    # Calculate total time and display statistics
    stats['total'] = time.time() - start_time
    print("\n" + "="*50)
    print("EXECUTION STATISTICS")
    print("="*50)
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
