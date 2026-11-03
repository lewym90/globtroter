import asyncio,sys
from playwright.async_api import async_playwright
async def main():
    svg=open('tools/icon.svg').read()
    async with async_playwright() as p:
        b=await p.chromium.launch()
        for name,size in (('icon-192',192),('icon-512',512),('apple-touch-icon',180),('icon-maskable-512',512)):
            pg=await b.new_page(viewport={'width':size,'height':size})
            await pg.set_content(f'<style>*{{margin:0}}svg{{display:block;width:{size}px;height:{size}px}}</style>{svg}')
            await pg.screenshot(path=f'icons/{name}.png')
            await pg.close()
        await b.close()
asyncio.run(main())
