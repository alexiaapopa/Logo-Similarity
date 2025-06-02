import re

# Citește din fișierul brut
with open("raw_websites.txt", "r", encoding="utf-8") as f:
    raw_data = f.read()

# Expresie regulată pentru domenii web
domains = re.findall(r'\b(?:[a-zA-Z0-9-]+\.)+[a-z]{2,}\b', raw_data)

# Elimină duplicatele
unique_domains = sorted(set(domains))

# Scrie în fișierul curățat
with open("cleaned_urls.txt", "w", encoding="utf-8") as f:
    for domain in unique_domains:
        f.write(f"https://{domain}\n")

print(f"Am extras {len(unique_domains)} domenii valide.")
