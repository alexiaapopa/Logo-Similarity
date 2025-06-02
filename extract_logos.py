import asyncio
import aiohttp
import aiofiles
from bs4 import BeautifulSoup
import os
from urllib.parse import urlparse, urljoin
import re

input_urls_file = "cleaned_websites.txt"
output_logos_dir = "downloaded_logos"
log_file = "download_log.txt"
error_file = "download_errors.txt"

os.makedirs(output_logos_dir, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,/;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive'
}

def get_clean_filename(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc if parsed_url.netloc else url
    domain = domain.replace('www.', '').split(':')[0]
    clean_name = re.sub(r'[^\w\-\. ]', '', domain)
    return f"{clean_name}.png"

async def url_exists(session, url):
    try:
        async with session.head(url, headers=HEADERS, timeout=5) as resp:
            return resp.status == 200
    except:
        return False

async def fetch_html(session, url):
    try:
        async with session.get(url, headers=HEADERS, timeout=15) as resp:
            resp.raise_for_status()
            text = await resp.text()
            return text
    except:
        return None

async def download_file(session, url, local_path):
    try:
        async with session.get(url, headers=HEADERS, timeout=15) as resp:
            resp.raise_for_status()
            f = await aiofiles.open(local_path, mode='wb')
            async for chunk in resp.content.iter_chunked(8192):
                await f.write(chunk)
            await f.close()
        return True
    except Exception as e:
        print(f"Download error {url}: {e}")
        return False

async def find_logo_url(session, soup, base_url):
    # 1. link-uri icon
    icon_links = soup.find_all('link', rel=['icon', 'shortcut icon', 'apple-touch-icon'])
    for link in icon_links:
        href = link.get('href')
        if href:
            logo_url = urljoin(base_url, href)
            if await url_exists(session, logo_url):
                return logo_url

    # 2. meta og:image
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        logo_url = urljoin(base_url, og_image.get('content'))
        if await url_exists(session, logo_url):
            return logo_url

    # 3. img cu atribute ce conțin 'logo'
    imgs = soup.find_all('img')
    for img in imgs:
        attrs = ' '.join([str(v).lower() for v in img.attrs.values()])
        if 'logo' in attrs:
            src = img.get('src')
            if src:
                logo_url = urljoin(base_url, src)
                if await url_exists(session, logo_url):
                    return logo_url

    # 4. Căi comune
    common_paths = ['/logo.png', '/logo.jpg', '/favicon.ico', '/assets/logo.png', '/images/logo.png']
    for path in common_paths:
        logo_url = urljoin(base_url, path)
        if await url_exists(session, logo_url):
            return logo_url

    return None

async def process_url(session, domain_url, total, index, sem):
    async with sem:
        if not domain_url.startswith(('http://', 'https://')):
            full_url = f"http://{domain_url}"
        else:
            full_url = domain_url

        local_logo_filename = os.path.join(output_logos_dir, get_clean_filename(domain_url))

        if os.path.exists(local_logo_filename) and os.path.getsize(local_logo_filename) > 0:
            print(f"[{index}/{total}] SKIPPED (exists): {domain_url}")
            async with aiofiles.open(log_file, 'a', encoding='utf-8') as lf:
                await lf.write(f"SKIPPED: {domain_url} (already exists)\n")
            return 'skipped'

        print(f"[{index}/{total}] Processing: {full_url}")

        html = await fetch_html(session, full_url)
        if not html:
            print(f"[{index}/{total}] ERROR: Failed to fetch {full_url}")
            async with aiofiles.open(error_file, 'a', encoding='utf-8') as ef:
                await ef.write(f"ERROR: {full_url} - Failed to fetch HTML\n")
            return 'error'

        soup = BeautifulSoup(html, 'html.parser')
        logo_url = await find_logo_url(session, soup, full_url)

        if logo_url:
            print(f"[{index}/{total}] Found logo: {logo_url}")
            success = await download_file(session, logo_url, local_logo_filename)
            if success:
                async with aiofiles.open(log_file, 'a', encoding='utf-8') as lf:
                    await lf.write(f"DOWNLOADED: {domain_url} -> {logo_url}\n")
                return 'downloaded'
            else:
                print(f"[{index}/{total}] ERROR: Failed to download logo for {domain_url}")
                async with aiofiles.open(error_file, 'a', encoding='utf-8') as ef:
                    await ef.write(f"ERROR: {domain_url} - Failed to download logo\n")
                return 'error'
        else:
            print(f"[{index}/{total}] ERROR: No logo found for {domain_url}")
            async with aiofiles.open(error_file, 'a', encoding='utf-8') as ef:
                await ef.write(f"ERROR: {domain_url} - No logo URL found\n")
            return 'error'

async def main():
    async with aiohttp.ClientSession() as session:
        with open(input_urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]

        sem = asyncio.Semaphore(10)  # Max 10 conexiuni simultane
        total = len(urls)
        tasks = []
        for i, url in enumerate(urls, start=1):
            tasks.append(process_url(session, url, total, i, sem))

        results = await asyncio.gather(*tasks)

        downloaded_count = results.count('downloaded')
        skipped_count = results.count('skipped')
        error_count = results.count('error')

        print("\n--- Summary ---")
        print(f"Total URLs processed: {total}")
        print(f"Logos downloaded: {downloaded_count}")
        print(f"Logos skipped (already existed): {skipped_count}")
        print(f"Errors / No logo found: {error_count}")
        print(f"Check '{log_file}' for successful downloads.")
        print(f"Check '{error_file}' for errors.")

if __name__ == "__main__":
    asyncio.run(main())