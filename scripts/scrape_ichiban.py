import re, json, sys, time, html, urllib.request, http.cookiejar

out = sys.argv[1]
base = "https://www.mobile-ichiban.com"
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36")]

first = op.open(base + "/Prod/2").read().decode("utf-8")
m = re.search(r'data-urlformat="([^"]+)"', first)
fmt = html.unescape(m.group(1))
pages = int(re.search(r'data-pagecount="(\d+)"', first).group(1))

card_re = re.compile(r'<div class="card-body.*?(?=<div class="col-6 col-md-4|\Z)', re.S)

def parse(doc):
    items = []
    for blk in card_re.findall(doc):
        titles = re.findall(r'title="([^"]*)" style="height:21px"', blk)
        jan = re.search(r'JAN:(\d+)', blk)
        newp = re.search(r'id="NewPrice_(S\d+)">\s*([\d,]+)円', blk)
        oldp = re.search(r'id="OldPrice_S\d+">\s*([\d,]+)円', blk)
        rem = re.search(r'my-prod-remarks[^>]*>\s*(.*?)&nbsp;', blk, re.S)
        if not titles or not newp:
            continue
        items.append({
            "id": newp.group(1),
            "name": html.unescape(titles[0]).strip(),
            "sub": html.unescape(titles[1]).strip() if len(titles) > 1 else "",
            "jan": jan.group(1) if jan else "",
            "buy": int(newp.group(2).replace(",", "")),
            "buy_used": int(oldp.group(1).replace(",", "")) if oldp else None,
            "remarks": html.unescape(rem.group(1)).strip() if rem else "",
        })
    return items

all_items = parse(first)
for p in range(2, pages + 1):
    url = base + fmt.replace("__id__", str(p))
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=b"", headers={"X-Requested-With": "XMLHttpRequest"})
            doc = op.open(req, timeout=30).read().decode("utf-8")
            break
        except Exception as e:
            time.sleep(2)
    got = parse(doc)
    print(p, len(got), file=sys.stderr)
    all_items += got
    time.sleep(0.5)

seen = {}
for it in all_items:
    seen.setdefault(it["id"], it)
print(len(seen))
# A short result means the site failed or changed layout; keep the previous ranking instead
if len(seen) < 1000:
    sys.exit("too few items: %d" % len(seen))
json.dump(list(seen.values()), open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
