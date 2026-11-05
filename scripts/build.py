import json, sys, csv, datetime

items_p, amz_p, tpl_p, html_out, csv_out = sys.argv[1:6]
# --standalone adds the document head that the Claude artifact host would otherwise supply
standalone = "--standalone" in sys.argv[6:]
JST = datetime.timezone(datetime.timedelta(hours=9))
items = json.load(open(items_p, encoding="utf-8"))
amz = json.load(open(amz_p, encoding="utf-8"))

rows = []
for it in items:
    a = amz.get(it["id"])
    res = (a or {}).get("results") or []
    pick = next((r for r in res if r["price"] and not r["sponsored"]), None) or next((r for r in res if r["price"]), None)
    if not pick or not it["buy"]:
        continue
    rate = it["buy"] / pick["price"] * 100
    # Ratio far outside a plausible band usually means the JAN search hit a different product
    flag = "" if 30 <= rate <= 130 else "要確認"
    rows.append({
        "name": it["name"], "sub": it["sub"], "jan": it["jan"], "remarks": it["remarks"],
        "buy": it["buy"], "amz": pick["price"], "rate": round(rate, 1),
        "asin": pick["asin"], "amzTitle": pick["title"], "flag": flag,
    })

rows.sort(key=lambda r: (r["flag"] != "", -r["rate"]))
for i, r in enumerate(rows, 1):
    r["rank"] = i

meta = {"date": datetime.datetime.now(JST).date().isoformat(), "amzDate": "2026-11-05", "total": len(items), "matched": len(rows),
        "flagged": sum(1 for r in rows if r["flag"])}
tpl = open(tpl_p, encoding="utf-8").read()
if standalone:
    tpl = ('<!doctype html>\n<html lang="ja">\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
           '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
           'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n' + tpl)
open(html_out, "w", encoding="utf-8").write(
    tpl.replace("__DATA__", json.dumps(rows, ensure_ascii=False)).replace("__META__", json.dumps(meta)))

with open(csv_out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["順位", "買取率(%)", "商品名", "備考", "JAN", "買取価格", "Amazon価格", "ASIN", "Amazon商品名", "判定"])
    for r in rows:
        w.writerow([r["rank"], r["rate"], r["name"] + (" " + r["sub"] if r["sub"] else ""), r["remarks"], r["jan"],
                    r["buy"], r["amz"], r["asin"], r["amzTitle"], r["flag"]])
print(meta)
