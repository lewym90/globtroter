"""Pelny przejazd aplikacji jak uzytkownik, z prawdziwym serwerem. python3 tests/flow.py miejsce"""
import asyncio,sys,json
from playwright.async_api import async_playwright
SP='/tmp/claude-0/-home-claude/73acc2db-ba8a-5377-807c-95ff6f04714f/scratchpad/'
place=sys.argv[1] if len(sys.argv)>1 else 'Barcelona'
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        c=await b.new_context(**{k:v for k,v in p.devices['iPhone 14 Pro'].items() if k!='default_browser_type'},geolocation={'latitude':51.2465,'longitude':22.5684},permissions=['geolocation'])
        pg=await c.new_page();errs=[]
        pg.on('console',lambda m:errs.append(m.text) if m.type=='error' else None);pg.on('pageerror',lambda e:errs.append('PE '+str(e)))
        await pg.goto('http://localhost:8000/');await pg.wait_for_timeout(900)
        await pg.click('#go');await pg.wait_for_timeout(300)
        await pg.click('#gps');await pg.wait_for_timeout(2500);await pg.screenshot(path=SP+'f1.png')
        await pg.click('#next');await pg.wait_for_timeout(300)
        await pg.click('[data-m=city]');await pg.fill('#p',place);await pg.wait_for_timeout(200)
        await pg.click('[data-add]');await pg.wait_for_timeout(200);await pg.screenshot(path=SP+'f2.png')
        await pg.click('#next');await pg.wait_for_timeout(300);await pg.click('[data-m2="2"]');await pg.wait_for_timeout(200);await pg.screenshot(path=SP+'f3.png')
        await pg.click('#next');await pg.wait_for_timeout(300);await pg.screenshot(path=SP+'f4.png')
        await pg.click('#next');await pg.wait_for_timeout(300);await pg.screenshot(path=SP+'f5.png')
        await pg.click('#next');await pg.wait_for_timeout(300);await pg.screenshot(path=SP+'f6.png')
        await pg.click('#next');await pg.wait_for_timeout(300);await pg.click('#next');await pg.wait_for_timeout(6000);await pg.screenshot(path=SP+'f7.png')
        await pg.wait_for_selector('[data-o],.note,.big',timeout=300000);await pg.wait_for_timeout(1200);await pg.screenshot(path=SP+'f8.png')
        await pg.click('[data-o]');await pg.wait_for_timeout(1200);await pg.screenshot(path=SP+'f9.png',full_page=True)
        await pg.click('#hot');await pg.wait_for_selector('.hot,.note',timeout=120000);await pg.wait_for_timeout(1500);await pg.screenshot(path=SP+'f10.png')
        await pg.click('[data-h]');await pg.wait_for_selector('.tabs',timeout=100000);await pg.wait_for_timeout(1500);await pg.screenshot(path=SP+'f11.png')
        await pg.evaluate("document.querySelector('#app').scrollTop=500");await pg.wait_for_timeout(300);await pg.screenshot(path=SP+'f12.png')
        for t in ('dni','koszty','lista','info'):
            await pg.click(f'[data-t={t}]');await pg.wait_for_timeout(400);await pg.screenshot(path=SP+f'f13{t}.png',full_page=True)
        print('bledy',errs[:8]);json.dump(await pg.evaluate('window.__gt.S.plan'),open(SP+'plan.json','w'),ensure_ascii=False)
        await b.close()
asyncio.run(main())
