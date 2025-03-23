import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor


BASE_URL = "https://www.archives.gov/research/jfk/release-2025"
DOWNLOAD_DIR = "jfk_files"
THREADS = 3 # change based on your PC


os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_pdf_links(url):
    """Scrapes the webpage for PDF links."""
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to access {url}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.endswith('.pdf'):
            links.append(urljoin(BASE_URL, href))
    return links

def download_file(url):
    
    filename = os.path.join(DOWNLOAD_DIR, os.path.basename(url))
    if os.path.exists(filename):
        print(f"Already downloaded: {filename}")
        return
    
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"Downloaded: {filename}")
    else:
        print(f"Failed to download: {url}")

def main():
    pdf_links = get_pdf_links(BASE_URL)
    if not pdf_links:
        print("No PDF links found.")
        return
    
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        executor.map(download_file, pdf_links)

if __name__ == "__main__":
    main()
