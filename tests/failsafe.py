"""Awarie i offline: serwer padl, plan bez internetu, wznawianie."""
import asyncio,json
from playwright.async_api import async_playwright
SP='/tmp/claude-0/-home-claude/73acc2db-ba8a-5377-807c-95ff6f04714f/scratchpad/'
plan=json.load(open(SP+'plan.json'))
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        c=await b.new_context(**{k:v for k,v in p.devices['iPhone 14 Pro'].items() if k!='default_browser_type'})
        pg=await c.new_page();errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('http://localhost:8000/');await pg.wait_for_timeout(1500)
        # 1 serwer niedostepny
        await pg.route('http://127.0.0.1:8796/**',lambda r:r.abort())
        await pg.evaluate("""()=>{const S=window.__gt.S;S.q.origin={lat:51,lon:22,label:'X'};}""")
        await pg.evaluate("document.querySelector('#go').click()");await pg.wait_for_timeout(300)
        for i in range(7):
            await pg.click('#next') if await pg.locator('#next').is_enabled() else None
            await pg.wait_for_timeout(120)
            if i==1 and await pg.locator('#next').count():
                pass
        await pg.wait_for_timeout(1200)
        t=await pg.inner_text('#app');print('SERWER PADL:',t[:140].replace('\n',' | '))
        await pg.unroute('http://127.0.0.1:8796/**')
        # 2 zapis planu i offline
        await pg.evaluate("p=>localStorage.setItem('gt.trips',JSON.stringify([p]))",plan)
        await pg.evaluate("navigator.serviceWorker.ready");await pg.wait_for_timeout(1500)
        await pg.reload();await pg.wait_for_timeout(1500)
        await c.set_offline(True)
        await pg.reload();await pg.wait_for_timeout(2000)
        print('OFFLINE START:',(await pg.inner_text('#app'))[:80].replace('\n',' | '))
        await pg.click('[data-trip]');await pg.wait_for_timeout(600)
        for t in('dni','koszty','lista','info','droga'):
            await pg.click(f'[data-t={t}]');await pg.wait_for_timeout(150)
        print('OFFLINE PLAN:',(await pg.inner_text('#body'))[:120].replace('\n',' | '))
        await pg.click('[data-t=lista]');await pg.click('[data-ck="0"]');await pg.reload();await pg.wait_for_timeout(1000);await pg.click('[data-trip]');await pg.click('[data-t=lista]')
        print('LISTA ZAPAMIETANA:',await pg.is_checked('[data-ck="0"]'))
        await c.set_offline(False)
        print('bledy',errs[:5]);await b.close()
asyncio.run(main())
