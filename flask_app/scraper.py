import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def clean_text(text):
    return " ".join(text.split())

def scrape_post(url):
    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "lxml")
        title = ""
        title_tag = soup.find("h3", class_="post-title")
        if title_tag:
            title = clean_text(title_tag.get_text())
        body = ""
        body_div = soup.find("div", class_="post-body")

        if body_div:
            body = clean_text(
                body_div.get_text(" ", strip=True)
            )
        date = ""

        date_tag = soup.find("h2", class_="date-header")

        if date_tag:
            date = clean_text(date_tag.get_text())

        return {
            "url": url,
            "title": title,
            "date": date,
            "content": body
        }

    except Exception as e:
        print(f"ERROR {url}: {e}")
        return None

def scrape_all_posts(urls, workers=10):
    results = []
    with ThreadPoolExecutor(
        max_workers=workers
    ) as executor:
        futures = {
            executor.submit(scrape_post, u): u
            for u in urls
        }
        completed = 0

        for future in as_completed(futures):
            post = future.result()
            completed += 1
            if completed % 100 == 0:
                print(
                    f"Scraped {completed}/{len(urls)}"
                )

            if post:
                results.append(post)
    return results
