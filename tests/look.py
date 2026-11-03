"""Zrzuty ekranu jak na iPhonie. python3 tests/look.py nazwa [skrypt.js]"""
import asyncio,sys
from playwright.async_api import async_playwright
async def main(name,js=None,wait=2200,full=False):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        c=await b.new_context(**{k:v for k,v in p.devices['iPhone 14 Pro'].items() if k!='default_browser_type'},geolocation={'latitude':51.2465,'longitude':22.5684},permissions=['geolocation'])
        pg=await c.new_page()
        errs=[]
        pg.on('console',lambda m:errs.append(m.text) if m.type=='error' else None);pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('http://localhost:8000/');await pg.wait_for_timeout(1200)
        if js: await pg.evaluate(js)
        await pg.wait_for_timeout(wait)
        await pg.screenshot(path=f'/tmp/claude-0/-home-claude/73acc2db-ba8a-5377-807c-95ff6f04714f/scratchpad/{name}.png',full_page=full)
        print('bledy',errs[:6]);await b.close()
asyncio.run(main(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None))
