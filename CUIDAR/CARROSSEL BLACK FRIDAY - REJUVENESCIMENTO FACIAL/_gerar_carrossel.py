import sys, pathlib
from playwright.sync_api import sync_playwright

SCR = pathlib.Path(r"C:\Users\artti\AppData\Local\Temp\claude\ab8f30d621de297d\2e553156-0c2a-461b-9d9c-3843996f1e02")
IMG = SCR / "images"
LOGO = SCR / "scratchpad" / "logo"
OUT = pathlib.Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

def u(p): return pathlib.Path(p).as_uri()

TOTAL = 7
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500;1,600&family=Montserrat:wght@300;400;500;600;700&display=block');
:root{--bg:#063b3d;--teal:#00565A;--gold:#D4B048;--gold2:#E9D08A;--cream:#F4EEE1;}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1350px;overflow:hidden;background:var(--bg)}
.card{position:relative;width:1080px;height:1350px;background:var(--bg);font-family:Montserrat,sans-serif;color:var(--cream);overflow:hidden}
.photo{position:absolute;left:0;top:0;width:1080px;object-fit:cover}
.shade-top{position:absolute;inset:0 0 auto 0;height:260px;background:linear-gradient(rgba(3,30,31,.55),rgba(3,30,31,0))}
.shade-bot{position:absolute;left:0;right:0;background:linear-gradient(rgba(6,59,61,0),var(--bg) 92%)}
.logo-foot{position:absolute;left:0;right:0;bottom:50px;display:flex;justify-content:center;align-items:center;gap:16px}
.logo-foot img.sym{height:62px}.logo-foot img.word{height:38px}
.swipe{position:absolute;right:52px;bottom:50px;width:62px;height:62px;border-radius:50%;border:2px solid rgba(255,255,255,.35);background:rgba(255,255,255,.08);display:flex;align-items:center;justify-content:center}
.pill{position:absolute;left:50%;transform:translateX(-50%);top:60px;background:var(--gold);color:#062e30;font-weight:700;font-size:21px;letter-spacing:.22em;padding:14px 26px 13px 30px;border-radius:40px}
.eyebrow{font-weight:600;font-size:22px;letter-spacing:.28em;color:var(--gold);text-transform:uppercase;display:flex;align-items:center;gap:20px}
.eyebrow:before{content:"";width:56px;height:2px;background:var(--gold)}
h1{font-family:'Cormorant Garamond',serif;font-weight:600;color:#fff;line-height:1.02;letter-spacing:-.005em}
h1 em{font-style:italic;color:var(--gold2);font-weight:500}
p.body{font-weight:300;font-size:30px;line-height:1.45;color:#E6DFCF}
.text{position:absolute;left:72px;right:72px}
.foot{position:absolute;left:72px;right:72px;bottom:56px;display:flex;justify-content:space-between;align-items:center;font-size:20px;letter-spacing:.2em;font-weight:500;color:rgba(244,238,225,.7)}
.foot b{color:var(--gold);font-weight:600}
.dots{display:flex;gap:10px}.dots i{width:10px;height:10px;border-radius:50%;background:rgba(244,238,225,.25)}.dots i.on{background:var(--gold);width:34px;border-radius:6px}
"""

def foot(n, swipe=True):
    logo = f'<div class="logo-foot"><img class="sym" src="{u(LOGO/"symbol_white.png")}"><img class="word" src="{u(LOGO/"word_white.png")}"></div>'
    arrow = ('<div class="swipe"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,.6)" '
             'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg></div>') if swipe else ''
    return logo + arrow

def brand():
    return ''

def page(inner):
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="card">{inner}</div></body></html>'

def cover():
    return page(f"""
<img class="photo" src="{u(IMG/'5.jpg')}" style="height:1350px;object-position:50% 30%">
<div class="shade-top"></div>
<div class="shade-bot" style="top:560px;height:790px;background:linear-gradient(rgba(6,59,61,0),rgba(6,59,61,.88) 45%,var(--bg) 70%)"></div>
{brand()}<div class="pill">BLACK FRIDAY</div>
<div class="text" style="top:842px">
  <div class="eyebrow">Semana especial</div>
  <h1 style="font-size:96px;margin:26px 0 26px">Sua beleza merece um cuidado <em>especial.</em></h1>
  <p class="body" style="font-size:29px;max-width:900px">Conheça os tratamentos da nossa <b style="font-weight:600;color:#fff">Semana Especial de Rejuvenescimento Facial Natural.</b></p>
</div>
{foot(1)}""")

def content(n, img, pos, eyebrow, title, body, size=74):
    return page(f"""
<img class="photo" src="{u(IMG/img)}" style="height:900px;object-position:50% {pos}%">
<div class="shade-top"></div>
<div class="shade-bot" style="top:620px;height:290px"></div>
{brand()}<div class="pill">BLACK FRIDAY</div>
<div class="text" style="top:880px">
  <div class="eyebrow">{eyebrow}</div>
  <h1 style="font-size:{size}px;margin:22px 0 22px">{title}</h1>
  <p class="body">{body}</p>
</div>
{foot(n)}""")

WA = '<svg viewBox="0 0 32 32" width="40" height="40"><path fill="#062e30" d="M16 3C8.8 3 3 8.7 3 15.8c0 2.5.7 4.9 2 7L3 29l6.4-2c2 1.1 4.3 1.7 6.6 1.7 7.2 0 13-5.7 13-12.8S23.2 3 16 3zm0 23.4c-2.1 0-4.1-.6-5.9-1.7l-.4-.3-3.8 1.2 1.2-3.7-.3-.4a10.4 10.4 0 0 1-1.7-5.7C5.1 10 10 5.3 16 5.3S26.9 10 26.9 15.8 22 26.4 16 26.4zm6-7.8c-.3-.2-1.9-1-2.2-1.1-.3-.1-.5-.2-.7.2l-1 1.2c-.2.2-.4.2-.7.1-.3-.2-1.4-.5-2.6-1.6-1-.9-1.6-1.9-1.8-2.2-.2-.3 0-.5.1-.7l.5-.6.3-.5v-.5l-1-2.4c-.3-.6-.5-.5-.7-.5h-.6c-.2 0-.6.1-.9.4-.3.3-1.1 1.1-1.1 2.7s1.2 3.2 1.3 3.4c.2.2 2.3 3.5 5.6 4.9.8.3 1.4.5 1.9.7.8.2 1.5.2 2.1.1.6-.1 1.9-.8 2.2-1.5.3-.7.3-1.4.2-1.5-.1-.2-.3-.3-.6-.4z"/></svg>'

def cta():
    return page(f"""
<div style="position:absolute;left:150px;top:150px;width:780px;height:580px;border:2px solid rgba(212,176,72,.55);border-radius:390px 390px 0 0;transform:translate(18px,-18px)"></div>
<img src="{u(IMG/'23.jpg')}" style="position:absolute;left:150px;top:150px;width:780px;height:580px;object-fit:cover;object-position:50% 38%;border-radius:390px 390px 0 0">
{brand()}<div class="pill">BLACK FRIDAY</div>
<div class="text" style="top:776px;text-align:center">
  <h1 style="font-size:64px">Sua <em>melhor versão</em> começa com um cuidado individualizado.</h1>
  <p class="body" style="font-size:27px;margin-top:22px;line-height:1.42">Durante nossa Black Friday, você encontra condições especiais para cuidar de si. <b style="font-weight:600;color:#fff">Agende sua avaliação facial gratuita</b> e descubra os tratamentos mais indicados para você.</p>
</div>
<div style="position:absolute;left:0;right:0;top:1084px;display:flex;justify-content:center">
  <div style="display:flex;align-items:center;gap:18px;background:var(--gold);color:#062e30;border-radius:60px;padding:20px 46px 20px 34px;box-shadow:0 10px 30px rgba(0,0,0,.25)">
    {WA}<div style="text-align:left"><div style="font-size:17px;font-weight:600;letter-spacing:.2em">AGENDE PELO WHATSAPP</div><div style="font-size:40px;font-weight:700;letter-spacing:.02em;line-height:1.1">(84) 8856-5510</div></div>
  </div>
</div>
{foot(7, swipe=False).replace('bottom:56px','bottom:40px')}""")

cards = [
    cover(),
    content(2, "8.jpg", 46, "Lábios", "Lábios mais hidratados, definidos e <em>naturais.</em>",
            "Cuidados que valorizam a beleza dos lábios, respeitando suas características e proporções."),
    content(3, "11.jpg", 30, "Olhar", "Um olhar mais leve e <em>descansado.</em>",
            "Tratamentos pensados para suavizar sinais de cansaço e valorizar a expressão do olhar."),
    content(4, "10.jpg", 40, "Contorno facial", "Mais <em>harmonia</em> para os traços do seu rosto.",
            "Procedimentos que ajudam a valorizar os contornos faciais, respeitando a individualidade de cada pessoa."),
    content(5, "22.jpg", 52, "Qualidade da pele", "Sua pele também merece <em>atenção.</em>",
            "Cuidados voltados à hidratação, firmeza e melhora da qualidade da pele."),
    content(6, "9.jpg", 45, "Linhas de expressão", "Suavize as marcas sem perder sua <em>essência.</em>",
            "Tratamentos que buscam amenizar linhas de expressão, preservando a naturalidade do rosto."),
    cta(),
]

with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1080, "height": 1350})
    for i, html in enumerate(cards, 1):
        f = OUT / f"_card{i}.html"
        f.write_text(html, encoding="utf-8")
        pg.goto(f.as_uri(), wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        ok = pg.evaluate("document.fonts.check('600 40px \"Cormorant Garamond\"')")
        # flag text overflow below footer
        bottom = pg.evaluate("Math.max(...[...document.querySelectorAll('.text')].map(e=>e.getBoundingClientRect().bottom))")
        pg.screenshot(path=str(OUT / f"card{i:02d}.png"))
        f.unlink()
        print(i, "font ok" if ok else "FONT FALLBACK", "text bottom", round(bottom))
    b.close()
