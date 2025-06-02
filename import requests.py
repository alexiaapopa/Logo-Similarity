import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

MAX_THREADS = 50 

def is_url_functional(url, timeout=5):
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return url
        elif resp.status_code in [403, 405, 301, 302, 999]:
            resp = requests.get(url, timeout=timeout, allow_redirects=True)
            if resp.status_code == 200:
                return url
    except requests.RequestException:
        pass
    return None

def normalize_url(url):
    return "http://" + url if not url.startswith("http") else url

def filter_urls_fast(input_file, output_file):
    with open(input_file, "r") as f:
        urls = [normalize_url(line.strip()) for line in f if line.strip()]
    total = len(urls)

    print(f"[INFO] Verific URL-uri cu {MAX_THREADS} thread-uri...\n")

    functional = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_url = {executor.submit(is_url_functional, url): url for url in urls}
        for i, future in enumerate(as_completed(future_to_url), 1):
            url = future_to_url[future]
            try:
                result = future.result()
                if result:
                    functional.append(result)
                    print(f"[OK]     ({i}/{total}) {url}")
                else:
                    print(f"[EROARE] ({i}/{total}) {url}")
            except Exception as e:
                print(f"[E] ({i}/{total}) {url} -> {e}")

    durata = time.time() - start_time
    procent = len(functional) / total * 100

    print(f"\n[FINAL] Funcționale: {len(functional)} / {total} ({procent:.2f}%)")
    print(f"[TIMP]   Total: {durata:.2f} secunde")

    if procent < 97:
        print("[ATENȚIE] Procent sub 97%! Verifică sursa URL-urilor.")
    else:
        print("[SUCCESS] Poți continua cu extracția logo-urilor.")

    with open(output_file, "w") as f:
        f.write('\n'.join(functional))

    print(f"[SALVAT] URL-uri funcționale scrise în: {output_file}")

if __name__ == "__main__":

    filter_urls_fast("urls.txt", "urls_functionale.txt")