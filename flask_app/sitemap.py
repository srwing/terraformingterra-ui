import requests
from bs4 import BeautifulSoup
import re
import time

BASE = "https://globalwarming-arclein.blogspot.com"

def fetch_sitemap_page(page=1):
    url = f"{BASE}/sitemap.xml?page={page}"
    print(f"Fetching sitemap page {page}")
    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
    if r.status_code != 200:
        return None
    return r.text

def extract_urls(xml_text):
    soup = BeautifulSoup(xml_text, "xml")
    urls = []
    for loc in soup.find_all("loc"):
        u = loc.text.strip()
        if re.search(r"/\d{4}/\d{2}/", u):
            urls.append(u)
    return urls

def discover_all_urls(max_pages=500):
    all_urls = set()
    for page in range(1, max_pages + 1):
        xml = fetch_sitemap_page(page)
        if not xml:
            break
        urls = extract_urls(xml)
        if not urls:
            break

        before = len(all_urls)
        all_urls.update(urls)
        after = len(all_urls)

        print(f"  Found {len(urls)} URLs")
        print(f"  Unique total: {after}")

        if after == before:
            break

        time.sleep(0.5)
    return sorted(all_urls)
