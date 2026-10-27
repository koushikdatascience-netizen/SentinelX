import {test,expect,Page} from "@playwright/test";

async function accountAndWorkspace(page:Page) {
 await page.goto("/");
 const email=`browser-${crypto.randomUUID()}@example.org`;
 await page.getByRole("button",{name:"New here? Create an account"}).click();
 await page.getByLabel("Email address").fill(email);
 await page.getByLabel("Password",{exact:true}).fill("StrongPassword123");
 await page.getByRole("button",{name:"Create account",exact:false}).click();
 await expect(page.getByRole("heading",{name:"Welcome back"})).toBeVisible();
 await page.getByRole("button",{name:"Sign in",exact:false}).first().click();
 await page.getByRole("button",{name:"Configuration",exact:true}).click();
 await page.getByLabel("Workspace name").fill("Browser demo workshop");
 await page.getByRole("button",{name:"Create workspace",exact:true}).click();
 await expect(page.getByLabel("Active workspace")).not.toHaveValue("");
 await page.getByRole("button",{name:"New analysis",exact:true}).click();
}

test("owner evidence, recorded review and downloadable audit",async({page})=>{
 await accountAndWorkspace(page);
 await page.getByRole("button",{name:"Generate evidence-backed audit"}).click();
 await expect(page.getByRole("heading",{name:"Intelligence history"})).toBeVisible();
 await expect(page.getByText("We create handmade solid-wood furniture",{exact:false}).first()).toBeVisible();
 await page.getByRole("button",{name:"Create proposal"}).click();
 await page.getByRole("button",{name:"Approve",exact:true}).click();
 await expect(page.getByText("approved",{exact:true})).toBeVisible();
 const downloadPromise=page.waitForEvent("download");
 await page.getByRole("button",{name:"Download audit report"}).click();
 const download=await downloadPromise;
 expect(download.suggestedFilename()).toMatch(/^sentinelx-.*\.md$/);
 const stream=await download.createReadStream();
 const chunks=[];for await(const chunk of stream!)chunks.push(chunk);
 const text=Buffer.concat(chunks).toString();
 expect(text).toContain("user_supplied_unverified");
 expect(text).toContain("approved (no external execution)");
});

test("mocked provider draft is validated, rendered and exported",async({page})=>{
 await accountAndWorkspace(page);
 await page.getByRole("checkbox",{name:/Enable explicit provider inference/}).check();
 await page.getByRole("button",{name:"Generate evidence-based draft"}).click();
 await expect(page.getByRole("heading",{name:"Offline fixture draft"})).toBeVisible();
 await expect(page.getByText(/mock_test_provider/)).toBeVisible();
 await expect(page.getByText("This is an offline browser test fixture, not real AI inference.")).toBeVisible();
 await page.evaluate(()=>window.scrollTo(0,0));
 await page.screenshot({path:"test-results/evidence-draft-desktop.png",fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await expect(page.getByRole("heading",{name:"Offline fixture draft"})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:"test-results/evidence-draft-mobile.png",fullPage:true});
 const downloadPromise=page.waitForEvent("download");
 await page.getByRole("button",{name:"Download audit report"}).click();
 const stream=await(await downloadPromise).createReadStream();
 const chunks=[];for await(const chunk of stream!)chunks.push(chunk);
 expect(Buffer.concat(chunks).toString()).toContain("Offline fixture draft");
 await page.getByRole("button",{name:"New analysis",exact:true}).click();
 await page.getByRole("button",{name:"Generate evidence-based draft"}).click();
 await expect(page.getByRole("heading",{name:"Offline fixture draft"})).toBeVisible();
 await page.getByRole("button",{name:"Sign out",exact:true}).last().click();
 await expect(page.getByRole("heading",{name:"Welcome back"})).toBeVisible();
});


test("public sample works without authentication or provider requests",async({page})=>{
 const apiCalls:string[]=[];
 page.on("request",r=>{if(r.url().includes("/api/"))apiCalls.push(r.url())});
 await page.goto("/demo");
 await expect(page.getByRole("heading",{name:"Turn workshop facts into a campaign you can review."})).toBeVisible();
 await page.getByRole("button",{name:"Approve sample pack",exact:true}).click();
 await expect(page.getByRole("status")).toHaveText("approved");
 const promise=page.waitForEvent("download");
 await page.getByRole("button",{name:"Download sample campaign pack"}).click();
 expect((await promise).suggestedFilename()).toBe("sentinelx-sample-campaign.md");
 expect(apiCalls).toEqual([]);
});

test("Business Studio creates campaign, landing, approval and export in offline fixture mode",async({page})=>{
 await accountAndWorkspace(page);
 await page.getByRole("button",{name:"Business Studio",exact:true}).click();
 await expect(page.getByRole("heading",{name:"From business insight to launch-ready assets."})).toBeVisible();
 await page.getByRole("button",{name:/Generate business audit & campaign/}).click();
 await expect(page.getByRole("heading",{name:"Business opportunity audit"})).toBeVisible();
 await expect(page.getByText("sample",{exact:true}).first()).toBeVisible();
 await page.getByRole("button",{name:/Review seven-day plan/}).click();
 await expect(page.locator(".studio-day")).toHaveCount(7);
 await page.getByRole("button",{name:/Build a landing page/}).click();
 await page.getByRole("button",{name:/Generate page draft/}).click();
 await expect(page.locator("iframe[title='Landing preview']")).toBeVisible();
 await page.getByRole("button",{name:/Review approvals/}).click();
 await expect(page.getByRole("heading",{name:/Approval board & delivery pack/})).toBeVisible();
 const landing=page.locator(".studio-review").filter({hasText:"landing"}).first();
 await landing.getByRole("button",{name:"Approve"}).click();
 await expect(page.getByText(/Decision approved recorded/)).toBeVisible();
 const promise=page.waitForEvent("download");
 await page.getByRole("button",{name:/Download approved campaign pack/}).click();
 expect((await promise).suggestedFilename()).toBe("sentinelx-approved-pack.zip");
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:"test-results/business-studio-mobile.png",fullPage:true});
});
