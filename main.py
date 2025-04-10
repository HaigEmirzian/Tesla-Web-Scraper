import os
import hashlib
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup, Comment
from plyer import notification


# Fetch the page content and extract the body HTML
def fetch_page_content(playwright, url):
    try:
        browser = playwright.firefox.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url, timeout=30000, wait_until="load")
        # Extract only the body content
        content = page.inner_html("body")
        browser.close()
        return content
    except Exception as e:
        print(f"[ERROR] Failed to fetch {url} with Playwright: {e}")
        return None


# Clean up the HTML to remove unnecessary dynamic content
def clean_html(content):
    soup = BeautifulSoup(content, 'html.parser')

    # Remove script, style tags, and inline styles
    for script in soup(['script', 'style']):
        script.decompose()
    
    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove dynamic timestamps or any elements with classes that change frequently
    for dynamic in soup.find_all(class_="dynamic-class"):
        dynamic.decompose()

    # Remove elements that are frequently updated (e.g., social media embeds, ads)
    for ad in soup.find_all(['iframe', 'advertisement', 'social-media']):
        ad.decompose()

    return str(soup)


# Generate a hash of the content for comparison
def get_content_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


# Compare the current page content with the saved snapshot
def check_for_changes(new_content, old_snapshot_path):
    try:
        with open(old_snapshot_path, 'r', encoding='utf-8') as file:
            old_content = file.read()
            if get_content_hash(new_content) != get_content_hash(old_content):
                return True  # Content has changed
            else:
                return False  # No change
    except FileNotFoundError:
        return True  # If no previous snapshot exists, assume change


# Save the current content as a snapshot
def save_snapshot(content, snapshot_path):
    with open(snapshot_path, 'w', encoding='utf-8') as file:
        file.write(content)


# Send a desktop notification
def send_notification(url):
    notification.notify(
        title="🚨 Tesla Website Change Detected 🚨",
        message=f"Changes were detected on: {url}",
        timeout=3  # Duration the notification will be visible (seconds)
    )


# Main function to run the scraper and check for updates
def main():
    # Load the URLs to check
    urls_file = "urls.txt"
    with open(urls_file, "r") as file:
        urls = file.readlines()

    # Check each URL for changes
    with sync_playwright() as playwright:
        for url in urls:
            url = url.strip()
            if not url:
                continue
            snapshot_filename = f"snapshots/{url.replace('https://', '').replace('www.', '').replace('/', '_')}.html"
            print(f"[INFO] Checking {url}...")

            # Fetch and clean page content
            content = fetch_page_content(playwright, url)
            if not content:
                print(f"[ERROR] Failed to fetch {url}. Skipping...")
                continue

            cleaned_content = clean_html(content)

            # Check for changes by comparing the hash of the content
            if check_for_changes(cleaned_content, snapshot_filename):
                print(f"🚨 [CHANGED] {url}")
                send_notification(url)
                # Save the new snapshot
                save_snapshot(cleaned_content, snapshot_filename)
            else:
                print(f"[OK] No change at {url}")


if __name__ == "__main__":
    # Create snapshots folder if it doesn't exist
    if not os.path.exists("snapshots"):
        os.makedirs("snapshots")

    main()
