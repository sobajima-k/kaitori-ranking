"""Amazon.co.jp の価格を JAN 検索で取得する（ローカル実行用。Amazon はクラウドからのアクセスを弾きやすい）

使い方: python -I scripts/amz_fetch.py data/ichiban.json <出力json>
出力ファイルは途中保存も兼ねるので、中断しても同じコマンドで続きから取得できる。
"""
import urllib.request, urllib.parse, re, gzip, json, sys, os, time, html, random
from concurrent.futures import ThreadPoolExecutor

src, cache_path = sys.argv[1], sys.argv[2]
items = json.load(open(src, encoding="utf-8"))
cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
     "Accept-Language": "ja-JP,ja;q=0.9", "Accept": "text/html,application/xhtml+xml", "Accept-Encoding": "gzip"}

def fetch(q):
    url = "https://www.amazon.co.jp/s?k=" + urllib.parse.quote(q)
    for attempt in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=25)
            d = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                d = gzip.decompress(d)
            d = d.decode("utf-8", "ignore")
            if "captcha" in d.lower() and "s-search-result" not in d:
                raise RuntimeError("captcha")
            return d
        except Exception:
            time.sleep(5 * (attempt + 1) + random.random() * 3)
    return None

def parse(d):
    results = []
    for b in d.split('data-component-type="s-search-result"')[1:5]:
        b = b[:60000]
        title = re.search(r'<h2[^>]*aria-label="([^"]+)"', b) or re.search(r'<h2.*?<span[^>]*>(.*?)</span>', b, re.S)
        price = re.search(r'a-price-whole">([\d,]+)', b)
        asin = re.search(r'/dp/(\w{10})', b)
        results.append({
            "asin": asin.group(1) if asin else "",
            "title": html.unescape(re.sub(r"<.*?>", "", title.group(1))).strip() if title else "",
            "price": int(price.group(1).replace(",", "")) if price else None,
            "sponsored": "puis-sponsored-label" in b or "AdHolder" in b,
        })
    return results

def work(it):
    if it["id"] in cache:
        return
    q = it["jan"] or it["name"]
    time.sleep(random.random() * 1.5)
    d = fetch(q)
    cache[it["id"]] = {"q": q, "results": parse(d) if d else None}

todo = [it for it in items if it["id"] not in cache]
print("todo", len(todo), flush=True)
with ThreadPoolExecutor(4) as ex:
    for i, _ in enumerate(ex.map(work, todo)):
        if i % 50 == 0:
            json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
            print(i, flush=True)
json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
print("done", sum(1 for v in cache.values() if v["results"] is None), "failed")
