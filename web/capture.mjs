import {chromium,devices} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
await mkdir('../.impeccable/review',{recursive:true});
const browser=await chromium.launch({args:['--use-angle=swiftshader','--enable-webgl','--enable-unsafe-swiftshader']});
for(const [name,options] of [['desktop',{viewport:{width:1440,height:1000}}],['mobile',{...devices['iPhone 13']}]] ){
 const context=await browser.newContext({...options,deviceScaleFactor:1,reducedMotion:'reduce'});const page=await context.newPage();
 await page.goto('http://127.0.0.1:5173');
 await page.getByText('Demonstration dataset',{exact:true}).waitFor();
 await page.locator('.chart svg').first().waitFor();
 await page.locator('.map-frame[data-loaded="true"]').waitFor();
 await page.waitForTimeout(1500);
 await page.screenshot({path:`../.impeccable/review/${name}.png`,fullPage:true});
 await page.getByRole('tab',{name:'Competitive Analysis'}).click();
 await page.getByRole('cell',{name:'Pacific Coast Realty',exact:true}).last().waitFor();
 await page.evaluate(()=>window.scrollTo(0,0));await page.waitForTimeout(600);
 await page.screenshot({path:`../.impeccable/review/${name}-competitive.png`,fullPage:true});
 await context.close();
}
await browser.close();
