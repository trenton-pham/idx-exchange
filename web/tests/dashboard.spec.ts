import {test,expect} from '@playwright/test';
test('filters persist across tabs and reload; charts and maps use the API',async({page,isMobile})=>{
 const failures:string[]=[];page.on('pageerror',e=>failures.push(e.message));
 await page.goto('/');await expect(page.getByText('Demonstration dataset',{exact:true})).toBeVisible();
 await expect(page.locator('.map-frame')).toHaveAttribute('data-loaded','true');
 await expect(page.getByRole('heading',{name:'The market, over time'})).toBeVisible();
 if(isMobile)await page.getByRole('button',{name:'Filter market'}).click();
 await page.getByLabel('County',{exact:true}).selectOption('Santa Clara');
 await expect(page.getByRole('heading',{name:'Santa Clara County',exact:true})).toBeVisible();
 await page.getByRole('tab',{name:'Competitive Analysis'}).click();
 await expect(page.getByRole('heading',{name:'Who is moving the market'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Top agents by properties sold'})).toBeVisible();
 await expect(page.getByRole('cell',{name:'Pacific Coast Realty',exact:true}).first()).toBeVisible();
 await page.reload();await expect(page.getByRole('tab',{name:'Competitive Analysis'})).toHaveAttribute('aria-selected','true');
 await expect(page.getByRole('heading',{name:'Santa Clara County',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Reset map to California'}).click();
 await expect(page.getByRole('heading',{name:'California',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 expect(failures).toEqual([]);
});
test('expired month recovery and keyboard tabs',async({page})=>{
 await page.goto('/?month=2020-01');
 await expect(page.getByText('This month is outside the available reporting period.')).toBeVisible();
 await page.getByRole('button',{name:'Use nearest available month'}).click();
 await expect(page.getByRole('alert')).toHaveCount(0);
 await page.getByRole('tab',{name:'Market Trends'}).focus();await page.keyboard.press('ArrowRight');
 await expect(page.getByRole('tab',{name:'Competitive Analysis'})).toBeFocused();
 await expect(page.getByRole('tab',{name:'Competitive Analysis'})).toHaveAttribute('aria-selected','true');
});

test('map selection and layers stay synchronized',async({page})=>{
 await page.goto('/');await expect(page.locator('.map-frame')).toHaveAttribute('data-loaded','true');
 const canvas=page.locator('.maplibregl-canvas');const box=await canvas.boundingBox();
 if(!box)throw new Error('Map canvas is missing');
 // Project a known Central Valley point using the map's published initial bounds.
 const world=(lng:number,lat:number)=>[(lng+180)/360,(1-Math.log(Math.tan(Math.PI/4+lat*Math.PI/360))/Math.PI)/2];
 const a=world(-124.5,42.05),b=world(-114.05,32.45),point=world(-120,37.5);
 const scale=Math.min((box.width-56)/(b[0]-a[0]),(box.height-56)/(b[1]-a[1]));
 await canvas.click({position:{x:box.width/2+(point[0]-(a[0]+b[0])/2)*scale,y:box.height/2+(point[1]-(a[1]+b[1])/2)*scale}});
 await expect(page).toHaveURL(/county=/);
 await page.getByLabel('Map metric').selectOption('concentration');
 await expect(page.locator('.map-frame')).toHaveAttribute('data-loaded','true');
 await page.getByRole('button',{name:'ZIP',exact:true}).click();
 await expect(page.locator('.map-frame')).toHaveAttribute('data-loaded','true');
 await expect(page.getByText('2020 ZCTAs',{exact:false}).first()).toBeVisible();
});

test('empty geography and recoverable API error preserve controls',async({page})=>{
 await page.goto('/?county=NoSuchCounty&tab=competitive');
 await expect(page.getByText('No matching sales in this selection.').first()).toBeVisible();
 await page.route('**/api/v1/summary?**',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:{message:'Temporary test interruption.'}})}));
 await page.goto('/?county=Santa%20Clara');
 await expect(page.getByRole('alert')).toContainText('Temporary test interruption.');
 await page.unroute('**/api/v1/summary?**');
 await page.getByRole('button',{name:'Try again'}).click();
 await expect(page.getByRole('alert')).toHaveCount(0);
 await expect(page.getByRole('heading',{name:'Santa Clara County',exact:true})).toBeVisible();
});
