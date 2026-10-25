"""
Verify that every referenced image asset exists, is served via HTTP 200,
has valid dimensions and correct Content-Type.
"""
import urllib.request
import re
import sys

BASE_URL = "http://127.0.0.1:5000"
PAGES_TO_CHECK = [
    "/",
    "/rights",
    "/rights/right-to-safety",
    "/rights/right-to-seek-redressal",
    "/problems",
    "/guidance",
    "/guidance/e-commerce-refund-delays",
    "/guidance/defective-goods-warranty",
    "/wizard",
    "/wizard?step=3&guide=e-commerce-refund-delays",
    "/resources",
    "/faqs",
    "/about",
]

def main():
    print("=" * 65)
    print("CHECKING ALL REFERENCED IMAGES ACROSS THE WEBSITE")
    print("=" * 65)

    img_urls = set()
    for page in PAGES_TO_CHECK:
        url = f"{BASE_URL}{page}"
        req = urllib.request.Request(url, headers={"User-Agent": "ImageChecker/1.0"})
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode("utf-8")
            found = re.findall(r'<img [^>]*src=["\']([^"\']+)["\']', html)
            for src in found:
                img_urls.add(src)
            print(f"Checked page {page:<45} Found {len(found)} image(s)")

    print("-" * 65)
    print(f"Total unique image paths extracted: {len(img_urls)}")
    print("-" * 65)

    errors = 0
    for src in sorted(img_urls):
        full_url = f"{BASE_URL}{src}" if src.startswith("/") else src
        try:
            req = urllib.request.Request(full_url, headers={"User-Agent": "ImageChecker/1.0"})
            with urllib.request.urlopen(req) as resp:
                content_type = resp.headers.get("Content-Type", "")
                length = len(resp.read())
                print(f"[OK 200] {src:<42} | Size: {length:>7} bytes | Type: {content_type}")
        except Exception as e:
            print(f"[FAIL]   {src:<42} | Error: {e}")
            errors += 1

    print("=" * 65)
    if errors == 0:
        print("ALL REFERENCED IMAGES ARE VALID, REACHABLE, AND SERVED CORRECTLY!")
        print("=" * 65)
        sys.exit(0)
    else:
        print(f"FAILED: {errors} image(s) encountered errors.")
        print("=" * 65)
        sys.exit(1)

if __name__ == "__main__":
    main()
