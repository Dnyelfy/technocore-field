"""Alani sahte bir odaya karsi calistirir.

Kontroller:
  1. Figurler ciziliyor mu, konusma balonlari gercek metni gosteriyor mu
  2. Ayni cumleyi tekrarlayan farkli anahtarlar sari isaretleniyor mu
  3. Ilk yukleme hiz seridinde sahte bir zirve yaratmiyor mu
  4. Okuma coktugunde alan ekranda kaliyor mu
"""
import json, os, http.server, socketserver, threading, functools
from playwright.sync_api import sync_playwright

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")
DUP = "Another day, another check-in. The decentralized AI vision is compelling."
MSGS = [
    {"seq": 1, "from": "did:key:z6MkAlphaAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "text": DUP},
    {"seq": 2, "from": "did:key:z6MkBravoBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", "text": DUP},
    {"seq": 3, "from": "did:key:z6MkCharlieCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC", "text": DUP},
    {"seq": 4, "from": "alice", "text": "gm, anyone actually building here?"},
    {"seq": 5, "from": "did:key:z6MkDeltaDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",
     "text": "faucet — using previously learned faucet command"},
]
state = {"mode": "ok"}

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(("127.0.0.1", 8082), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

def route(r):
    if state["mode"] == "fail":
        r.fulfill(status=502, content_type="application/json", body='{"error":"upstream 503"}')
        return
    r.fulfill(status=200, content_type="application/json",
              body=json.dumps({"room": "lobby", "last_seq": 5, "messages": MSGS}))

fails = []
with sync_playwright() as pw:
    b = pw.chromium.launch()
    page = b.new_context(viewport={"width": 1240, "height": 860},
                         device_scale_factor=2).new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:200]))
    page.route("**/api/feed**", route)
    page.goto("http://127.0.0.1:8082/index.html")
    page.wait_for_timeout(2600)

    got = page.evaluate("""() => {
        const c = document.getElementById('field');
        const g = c.getContext('2d');
        const d = g.getImageData(0, 0, c.width, Math.round(c.height * 0.72)).data;
        let green = 0, amber = 0, white = 0;
        for (let i = 0; i < d.length; i += 4) {
            const r = d[i], gg = d[i+1], bb = d[i+2];
            if (gg > 190 && r > 110 && r < 170 && bb < 130) green++;
            else if (r > 210 && gg > 170 && bb < 120) amber++;
            else if (r > 200 && gg > 205 && bb > 195) white++;   // balon %92 saydam, zeminle karisiyor
        }
        return { green, amber, white };
    }""")
    print(f"  imzali figür pikseli: {got['green']} · tekrar eden (sarı): {got['amber']} · balon: {got['white']}")
    if got["amber"] < 20:
        fails.append("aynı cümleyi tekrarlayan anahtarlar sarı işaretlenmemiş")
    if got["white"] < 500:
        fails.append("konuşma balonu çizilmemiş")

    strip = page.evaluate("""() => {
        const c = document.getElementById('field');
        const g = c.getContext('2d');
        const d = g.getImageData(0, Math.round(c.height*0.85), c.width, 20).data;
        // Dolgu gradyaninin tepesi ~99; yer tutucu yazi 81. Esik ikisini ayirir.
        let lit = 0;
        for (let i = 0; i < d.length; i += 4) if (d[i+1] > 95 && d[i+1] > d[i] + 20) lit++;
        return lit;
    }""")
    print(f"  ilk yükleme sonrası hız şeridi dolgusu: {strip} (0'a yakın olmalı)")
    if strip > 400:
        fails.append("ilk yükleme hız şeridinde sahte zirve yaratmış")

    page.screenshot(path="/mnt/user-data/outputs/technocore-field.png")

    state["mode"] = "fail"
    page.wait_for_timeout(5000)
    st = page.inner_text("#state")
    still = page.evaluate("""() => {
        const c = document.getElementById('field');
        const d = c.getContext('2d').getImageData(0,0,c.width,Math.round(c.height*0.72)).data;
        let n = 0;
        for (let i = 0; i < d.length; i += 4) if (d[i+1] > 150) n++;
        return n;
    }""")
    print(f"  okuma çöktü → {st[:52]!r} · alanda kalan piksel: {still}")
    if still < 200:
        fails.append("okuma çöktüğünde alan boşaldı")
    if "failed" not in st:
        fails.append("okuma çöktü ama durum söylemiyor")

    print("  pageerror:", errs[:2] or "(yok)")
    if errs:
        fails.append("pageerror: " + errs[0])
    b.close()

httpd.shutdown()
print("\nSONUC:", "HEPSI GECTI" if not fails else "BASARISIZ")
for f in fails:
    print(" -", f)
