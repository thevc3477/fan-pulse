import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else 'file:///workspace/fan_pulse/index.html'
prefix = sys.argv[2] if len(sys.argv) > 2 else 'preview'

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    for name, w, h, m in [('desktop', 1440, 900, False), ('mobile', 390, 844, True)]:
        pg = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=1 if not m else 2, is_mobile=m)
        errors = []
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(url, wait_until='networkidle')
        pg.wait_for_timeout(1200)
        out_path = f'/workspace/fan_pulse/{prefix}_{name}.png'
        pg.screenshot(path=out_path, full_page=True)
        sh = pg.evaluate('document.body.scrollHeight')
        sw = pg.evaluate('document.documentElement.scrollWidth')
        iw = pg.evaluate('window.innerWidth')
        print(f"{name}: height={sh}px scrollWidth={sw}px innerWidth={iw}px overflow={sw > iw} errors={errors} -> {out_path}")
    b.close()
