"""Submit newly published article URLs to IndexNow (Bing, Yandex, etc.).

Reads one article slug per line from stdin and pings the IndexNow bulk
endpoint so those engines pick up the new pages without waiting on a
regular crawl. Google does not support IndexNow and is unaffected.
"""
import json
import sys
import urllib.error
import urllib.request

SITE = "https://www.cryptocatalyst.news"
HOST = "www.cryptocatalyst.news"
KEY = "258d94704f14111a42f0f410c6f0104c"


def main() -> None:
    slugs = [line.strip() for line in sys.stdin if line.strip()]
    if not slugs:
        print("IndexNow: no new URLs to submit")
        return

    url_list = [f"{SITE}/articles/{slug}" for slug in slugs]
    url_list.append(SITE)  # homepage digest changed too

    payload = json.dumps(
        {
            "host": HOST,
            "key": KEY,
            "keyLocation": f"{SITE}/{KEY}.txt",
            "urlList": url_list,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"IndexNow: submitted {len(url_list)} URL(s), status {resp.status}")
    except urllib.error.HTTPError as e:
        print(f"IndexNow: submission failed ({e.code}): {e.read().decode(errors='ignore')}")
    except urllib.error.URLError as e:
        print(f"IndexNow: submission failed: {e.reason}")


if __name__ == "__main__":
    main()
