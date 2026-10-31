import {test,expect,Page} from "@playwright/test";

test("owner entry offers account access without demo entry points",async({page})=>{
 await page.goto("/");
 await expect(page.getByRole("heading",{name:"Understand your business. Act with evidence."})).toBeVisible();
 await expect(page.getByRole("heading",{name:"Welcome back"})).toBeVisible();
 await expect(page.getByRole("button",{name:/^Sign in(?:\s*→)?$/})).toHaveCount(1);
 await expect(page.getByRole("button",{name:/demo|sample workspace/i})).toHaveCount(0);
 await expect(page.getByRole("link",{name:/sample|demo|tour/i})).toHaveCount(0);
 await expect(page.getByText("01 Business audit")).toBeVisible();
});


async function openTool(page:Page,title:string){
 const card=page.locator(".tool-card").filter({hasText:title});
 if(!await card.isVisible())await page.getByRole("button",{name:"Browse business tools",exact:true}).click();
 await card.click();
}

async function accountAndWorkspace(page:Page) {
 await page.goto("/");
 const email=`browser-${crypto.randomUUID()}@example.org`;
 await page.getByRole("button",{name:"New here? Create an account"}).click();
 await page.getByLabel("Email address").fill(email);
 await page.getByLabel("Password",{exact:true}).fill("StrongPassword123");
 await page.getByRole("button",{name:"Create account",exact:false}).click();
 await expect(page.getByRole("heading",{name:"Let’s get to know your business"})).toBeVisible();
 await expect(page.getByRole("heading",{name:"Your business workspace"})).toHaveCount(0);
 await page.getByLabel("Business name",{exact:true}).fill("Browser workshop");
 await page.getByLabel("Industry",{exact:true}).selectOption("Arts & crafts");
 await page.getByRole("button",{name:"Save & continue"}).click();
 await expect(page.getByRole("heading",{name:"Start discovering your brand?"})).toBeVisible();
 await page.getByRole("button",{name:"Skip for now"}).click();
 await expect(page.getByLabel("Active workspace")).not.toHaveValue("");
 await page.getByRole("button",{name:"Evidence reports",exact:true}).click();
 await page.getByLabel("Business website").fill("https://fixture.example/");
 await page.getByLabel("Business objective").fill("Improve qualified enquiries from local homeowners");
 await page.getByLabel("Page title").fill("Fixture Workshop — Handmade Furniture");
 await page.getByLabel("Owner-supplied website text (unverified)").fill("We create handmade solid-wood furniture and custom cabinetry. Customers can request consultations and quotations for bespoke projects.");
}

test("business onboarding skips collection, saves editable details and uploads, then starts background research explicitly",async({page})=>{
 const starts:string[]=[];
 page.on("request",request=>{if(request.method()==="POST"&&request.url().endsWith("/business-profile/research"))starts.push(request.url())});
 await accountAndWorkspace(page);
 expect(starts).toHaveLength(0);
 await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Business & research",exact:true}).click();
 await page.getByLabel("Business name",{exact:true}).fill("My saved workshop");
 await page.getByLabel("Industry",{exact:true}).selectOption("Other");
 await page.getByLabel("Your industry",{exact:true}).fill("Custom workshop components");
 await page.getByRole("button",{name:"Add social page"}).click();
 await page.getByLabel("Platform 1",{exact:true}).selectOption("instagram");
 await page.getByLabel("Page link 1",{exact:true}).fill("https://instagram.com/fixture-workshop");
 await page.getByText("Add a logo, images or business documents",{exact:false}).click();
 await page.getByLabel("Business logo",{exact:true}).setInputFiles({name:"logo.png",mimeType:"image/png",buffer:Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGOwiVoAAAIMATcAJ4DRAAAAAElFTkSuQmCC","base64")});
 await page.getByLabel("I am authorized to provide these business materials.",{exact:false}).check();
 await page.getByRole("button",{name:"Save business details",exact:true}).click();
 await expect(page.getByRole("status")).toContainText("Business details saved");
 expect(starts).toHaveLength(0);
 await page.getByRole("tab",{name:/Brand assets/}).click();
 await expect(page.getByRole("img",{name:"logo.png"})).toBeVisible();
 await page.reload();
 await expect(page.getByRole("heading",{name:"Business & research",exact:true})).toBeVisible();
 await expect(page.getByLabel("Business name",{exact:true})).toHaveValue("My saved workshop");
 await expect(page.getByLabel("Your industry",{exact:true})).toHaveValue("Custom workshop components");
 await expect(page.getByLabel("Page link 1",{exact:true})).toHaveValue("https://instagram.com/fixture-workshop");
 await page.getByRole("tab",{name:"Activity",exact:true}).click();
 await expect(page.getByText("No research requests have been made.",{exact:true})).toBeVisible();
 await page.getByRole("button",{name:"Start new research",exact:true}).click();
 await expect(page.getByRole("status")).toContainText("Research running");
 expect(starts).toHaveLength(1);
 await page.getByRole("tab",{name:"Activity",exact:true}).click();
 await expect(page.getByText("Research finished.",{exact:false})).toBeVisible({timeout:15000});
 await expect(page.getByText("Only owner-supplied information is available.",{exact:false})).toBeVisible();
});

test("business insights show actionable priorities, evidence, gaps and an export without new generation",async({page})=>{
 await accountAndWorkspace(page);
 const finding={source_id:"P1",quote:"Send your drawing for a quote.",observation:"Clarify what to send with an inquiry.",why:"A drawing alone may omit quantities and timing.",next_step:"Add quantity and required date beside the quote link.",priority:"high",area:"contact_journey",verification:"Check that the inquiry opens with drawing, quantity and date fields."};
 const report={pages:[],remaining_urls:[],activity:[],limitations:[],coverage:{pages_collected:1,screenshots_saved:0},search:null,visual_review:null,ai_status:"ready",insight_sources:[{id:"P1",url:"https://example.org/contact",title:"Contact page",text:finding.quote,origin:"retrieved_public_page"}],insights:{provenance:"live_meta",data:{summary:"Make trade inquiries easier to qualify.",strengths:[{...finding,observation:"Preserve the drawing request.",priority:"low"}],improvements:[finding],unknowns:["No conversion baseline supplied."]}}};
 Object.assign(report.insights.data,{competitor_comparisons:[{name:"Candidate Workshop",source_id:"W1",quote:"Bulk custom parts in Kalyani.",url:"https://example.org/competitor",relevance:"Matching offering and stated area.",comparison:"Compare order requirements and product clarity.",suggested_response:"Explain the information required for a quotation."}],keyword_opportunities:[{phrase:"custom wooden parts Kalyani",intent:"local",suggested_use:"Test a local product information page.",evidence:"hypothesis",source_id:"",quote:""}]});
 let generations=0;
 await page.route("**/business-profile/research",async route=>{if(route.request().method()==="GET")await route.fulfill({json:[{id:"fixture-insights",state:"completed",created_at:"2026-10-30T10:00:00Z",input_profile:{name:"Browser workshop"},report}]});else{generations++;await route.abort()}});
 await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Business & research",exact:true}).click();
 await page.getByRole("tab",{name:"Insights",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Your business improvement report"})).toBeVisible();
 await expect(page.getByText("high priority · AI suggested")).toBeVisible();
 await expect(page.getByText(finding.verification,{exact:false})).toBeVisible();
 await page.getByText("View supporting evidence · P1").click();
 await expect(page.getByRole("link",{name:"Contact page"})).toHaveAttribute("href","https://example.org/contact");
 await page.getByRole("button",{name:"Market & keywords",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Candidate Workshop",exact:true})).toBeVisible();
 await expect(page.getByText("custom wooden parts Kalyani",{exact:true})).toBeVisible();
 await page.screenshot({path:"test-results/business-market-insights.png",fullPage:true});
 await page.getByRole("button",{name:"Social coverage",exact:true}).click();
 await expect(page.getByText("Restricted social pages are not directly scraped",{exact:false})).toBeVisible();
 await page.getByRole("button",{name:"Gaps & verification",exact:true}).click();
 await expect(page.getByText("No conversion baseline supplied.",{exact:true})).toBeVisible();
 const pending=page.waitForEvent("download");await page.getByRole("button",{name:"Download report",exact:true}).click();
 const download=await pending;const stream=await download.createReadStream();const chunks=[];for await(const chunk of stream!)chunks.push(chunk);
 const text=Buffer.concat(chunks).toString();expect(text).toContain(finding.verification);expect(text).toContain("No edits were published");
 await page.reload();await page.getByRole("tab",{name:"Insights",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Your business improvement report"})).toBeVisible();
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:"test-results/business-insights-mobile.png",fullPage:true});
 expect(generations).toBe(0);
});

test("brand image review prepares an editable linked generation brief only after explicit consent",async({page})=>{
 await accountAndWorkspace(page);
 await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Business & research",exact:true}).click();
 await page.getByText("Add a logo, images or business documents",{exact:false}).click();
 await page.getByLabel("Business documents & images",{exact:true}).setInputFiles({name:"social-post.png",mimeType:"image/png",buffer:Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGOwiVoAAAIMATcAJ4DRAAAAAElFTkSuQmCC","base64")});
 await page.getByLabel("I am authorized to provide these business materials.",{exact:false}).check();
 await page.getByRole("button",{name:"Save business details",exact:true}).click();
 await expect(page.getByRole("status")).toContainText("Business details saved");
 await page.route("**/api/v1/campaigns/runtime",route=>route.fulfill({json:{live_enabled:true}}));
 const calls:Record<string,unknown>[]=[];
 const rows:unknown[]=[];
 await page.route("**/api/v1/workbench?*",route=>route.fulfill({json:rows}));
 await page.route("**/api/v1/workbench",async route=>{
  const body=route.request().postDataJSON();calls.push(body);
  const result=body.tool==="image_review"?{id:body.request_id,tool:"image_review",status:"completed",provenance:"live_meta",model:"mock-vision",source_asset_id:body.asset_id,data:{summary:"The subject is visible with room for visual improvement.",strengths:["Clear subject."],improvements:["Improve background separation."],post_guidance:"Keep the product visible in a mobile crop.",regeneration_prompt:"An original product composition with clear lighting and a simple background.",limitations:["No sales uplift measured."]}}:{id:body.request_id,tool:"image",status:"completed",provenance:"live_meta",model:"mock-image",data:{prompt:body.prompt},limitation:"New concept; not a pixel-preserving edit."};
  rows.unshift(result);await route.fulfill({status:201,json:result});
 });
 await page.getByRole("tab",{name:/Brand assets/}).click();
 await page.getByRole("button",{name:"Review image",exact:true}).click();
 let dialog=page.getByRole("dialog",{name:"Review & improve image",exact:true});
 await expect(dialog.getByRole("button",{name:"Generate",exact:true})).toBeDisabled();
 await dialog.getByLabel("I consent to sending this selected image to Meta for visual review.",{exact:true}).check();
 await dialog.getByRole("button",{name:"Generate",exact:true}).click();
 await expect(dialog.getByText("Improve background separation.",{exact:true})).toBeVisible();
 await page.screenshot({path:"test-results/brand-image-review.png"});
 expect(calls).toHaveLength(1);expect(calls[0].consent).toBe(true);
 await dialog.getByRole("button",{name:"Prepare improved visual",exact:true}).click();
 dialog=page.getByRole("dialog",{name:"Generate an improved concept",exact:true});
 await expect(dialog.getByRole("textbox",{name:"Your prompt",exact:true})).toHaveValue(/original product composition/);
 expect(calls).toHaveLength(1);
 await dialog.getByRole("textbox",{name:"Your prompt",exact:true}).fill("An improved original product concept with a cleaner background and natural light.");
 await dialog.getByRole("button",{name:"Generate",exact:true}).click();
 await expect(dialog.getByText("New concept; not a pixel-preserving edit.",{exact:true})).toBeVisible();
 expect(calls).toHaveLength(2);expect(calls[1].source_review_id).toBe(calls[0].request_id);
});

test("saved screenshot visual insights require consent, show design changes and prepare a linked brief",async({page})=>{
 await accountAndWorkspace(page);
 await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Business & research",exact:true}).click();
 await page.getByText("Add a logo, images or business documents",{exact:false}).click();
 await page.getByLabel("Business logo",{exact:true}).setInputFiles({name:"brand.png",mimeType:"image/png",buffer:Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGOwiVoAAAIMATcAJ4DRAAAAAElFTkSuQmCC","base64")});
 await page.getByLabel("I am authorized to provide these business materials.",{exact:false}).check();
 const upload=page.waitForResponse(r=>r.url().endsWith("/business-profile/assets")&&r.request().method()==="POST");
 await page.getByRole("button",{name:"Save business details",exact:true}).click();const asset=await (await upload).json();
 const report={pages:[],remaining_urls:[],activity:[],limitations:[],coverage:{pages_collected:0,screenshots_saved:0},search:null,visual_review:null as unknown,visual_status:"not_requested",ai_status:"ready",insights:{provenance:"live_meta",data:{summary:"Saved text findings.",strengths:[],improvements:[],unknowns:["Layout not yet reviewed."],competitor_comparisons:[{name:"Candidate Workshop",url:"https://candidate.example/"}]}}};
 const original={id:"saved-visual-source",state:"partial",created_at:"2026-10-30T10:00:00Z",input_profile:{name:"Browser workshop",industry:"Arts & crafts",socials:[]},report};
 let jobs=[original];const requests:Record<string,unknown>[]=[];let recollections=0;
 await page.route("**/api/v1/campaigns/runtime",route=>route.fulfill({json:{live_enabled:true}}));
 await page.route("**/business-profile/research",async route=>{if(route.request().method()==="GET")await route.fulfill({json:jobs});else{recollections++;await route.abort()}});
 await page.route("**/research/*/visual-insights",async route=>{
  const body=route.request().postDataJSON();requests.push(body);
  const result={...original,id:"saved-visual-result",state:"completed",report:{...report,visual_status:"ready",visual_review:{provenance:"live_meta",model:"mock-vision",data:{summary:"Clarify the visible product hierarchy and improve the mobile presentation.",findings:[{image_index:1,area:"logo",priority:"medium",observation:"The visible brand mark needs more breathing room.",suggested_improvement:"Add clear space around the logo and keep it readable at phone size.",why:"Clear separation makes the brand easier to recognize.",verification:"Check the draft logo at desktop and phone sizes.",regeneration_prompt:"Create an original brand presentation concept with ample clear space and a legible mark."}]},panels:[{image_index:1,asset_id:asset.id,role:"business",kind:"logo",source_url:""}]}}};
  jobs=[result];await route.fulfill({status:202,json:result});
 });
 await page.reload();await page.getByRole("tab",{name:"Visual design",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Visual report has not been requested",exact:true})).toBeVisible();
 expect(requests).toHaveLength(0);
 await page.getByRole("button",{name:"Choose visual review",exact:true}).click();
 const consentDialog=page.getByRole("dialog",{name:"Request visual design insights",exact:true});
 await expect(consentDialog.getByRole("option",{name:/Candidate Workshop/})).toHaveCount(1);
 await expect(consentDialog.getByRole("button",{name:"Generate visual report · 1 AI request",exact:true})).toBeDisabled();
 await consentDialog.getByRole("checkbox").check();
 await consentDialog.getByRole("button",{name:"Generate visual report · 1 AI request",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Visual design & image insights",exact:true})).toBeVisible();
 await expect(page.locator(".visual-insight-copy")).toContainText("Clear separation makes the brand easier to recognize.");
 expect(requests).toHaveLength(1);expect(requests[0].consent).toBe(true);expect(requests[0].competitor_url).toBe("");expect(recollections).toBe(0);
 const download=page.waitForEvent("download");await page.getByRole("button",{name:"Download visual report",exact:true}).click();
 expect((await download).suggestedFilename()).toBe("sentinelx-visual-improvement-report.md");
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:"test-results/visual-design-report-mobile.png",fullPage:true});
 await page.getByRole("button",{name:"Prepare editable brief",exact:true}).click();
 await expect(page.getByRole("dialog",{name:"Generate an improved concept",exact:true}).getByRole("textbox",{name:"Your prompt",exact:true})).toHaveValue(/original brand presentation/);
 expect(requests).toHaveLength(1);expect(recollections).toBe(0);
});

test("social-only businesses request a consented platform report and prepare content without extra inference",async({page})=>{
 await accountAndWorkspace(page);
 await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Business & research",exact:true}).click();
 await page.getByRole("button",{name:"Add social page",exact:true}).click();
 await page.getByLabel("Platform 1",{exact:true}).selectOption("instagram");await page.getByLabel("Page link 1",{exact:true}).fill("https://instagram.com/workshop");
 await page.getByLabel("I am authorized to provide these business materials.",{exact:false}).check();
 await page.getByRole("button",{name:"Save business details",exact:true}).click();await expect(page.getByRole("status")).toContainText("Business details saved");
 await page.route("**/api/v1/campaigns/runtime",route=>route.fulfill({json:{live_enabled:true}}));
 let jobs:unknown[]=[];const calls:Record<string,unknown>[]=[];
 await page.route("**/business-profile/research",route=>route.fulfill({json:jobs}));
 await page.route("**/research/*/social-insights",async route=>{
  const body=route.request().postDataJSON();calls.push(body);
  const item={id:"social-report",state:"completed",created_at:"2026-10-30T10:00:00Z",input_profile:{name:"Browser workshop",socials:[]},report:{pages:[],remaining_urls:[],activity:[],limitations:[],coverage:{pages_collected:0,screenshots_saved:0},insights:null,visual_review:null,social_research:{status:"ready",attempts:[{platform:"instagram",url:"https://instagram.com/workshop",status:"completed"}],sources:[{id:"S1.W1",profile_url:"https://instagram.com/workshop",url:"https://instagram.com/workshop",text:"Custom parts made to order.",origin:"search_pointer"}],report:{provenance:"live_meta",data:{platforms:[{platform:"instagram",url:"https://instagram.com/workshop",coverage:"indexed_profile_evidence",summary:"Clarify the quote journey for trade customers on Instagram.",findings:[{source_id:"S1.W1",quote:"Custom parts made to order.",observation:"The indexed profile identifies the custom offering.",change:"Test a more specific inquiry invitation.",why:"A concrete next step may help buyers send requirements.",verification:"Compare qualified inquiries with a recorded baseline."}],competitor_examples:[],experiments:[{format:"Reel",topic:"Show a complete workshop inquiry",hook:"What should you send for a quote?",call_to_action:"Send your design and quantity.",measure:"Count complete inquiries; growth remains unmeasured."}],unknowns:["Full feeds and private analytics were not accessed."]}]}}}}};
  jobs=[item];await route.fulfill({status:202,json:item});
 });
 await page.reload();await page.getByRole("tab",{name:"Social insights",exact:true}).click();
 await page.getByRole("button",{name:"Research social profiles",exact:true}).click();
 const dialog=page.getByRole("dialog",{name:"Research social platforms",exact:true});
 await expect(dialog.getByRole("button",{name:"Start platform research",exact:true})).toBeDisabled();
 await dialog.getByLabel("I consent to public research and Meta processing",{exact:false}).check();
 await dialog.getByRole("button",{name:"Start platform research",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Instagram improvement report",exact:true})).toBeVisible();
 await expect(page.getByRole("heading",{name:"Show a complete workshop inquiry",exact:true})).toBeVisible();
 expect(calls).toHaveLength(1);expect(calls[0].urls).toEqual(["https://instagram.com/workshop"]);
 await page.screenshot({path:"test-results/social-platform-insights.png",fullPage:true});
 await page.getByRole("button",{name:"Prepare content draft",exact:true}).click();
 const draft=page.getByRole("dialog",{name:"Create a platform content draft",exact:true});
 await expect(draft.getByRole("combobox",{name:"Platform",exact:true})).toHaveValue("instagram");
 await expect(draft.getByRole("textbox",{name:"Your prompt",exact:true})).toHaveValue(/Show a complete workshop inquiry/);
 expect(calls).toHaveLength(1);
});

test("owner evidence, recorded review and downloadable audit",async({page})=>{
 await accountAndWorkspace(page);
 await page.getByRole("button",{name:"Generate evidence-backed audit"}).click();
 await expect(page.getByRole("heading",{name:"Report history"})).toBeVisible();
 await expect(page.getByText("We create handmade solid-wood furniture",{exact:false}).first()).toBeVisible();
 await page.getByLabel("Proposed action").fill("Prepare an improved homepage CTA for owner approval");
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

test("single business consent wraps on mobile and research progress opens in a modal",async({page})=>{
 await accountAndWorkspace(page);
 const nav=page.getByRole("navigation",{name:"Main navigation"});
 await nav.getByRole("button",{name:"Business & research",exact:true}).click();
 const consent=page.getByLabel("I am authorized to provide these business materials.",{exact:false});
 await expect(consent).toHaveCount(1);
 await page.setViewportSize({width:390,height:844});
 await consent.check();await expect(consent).toBeChecked();
 await consent.uncheck();await expect(consent).not.toBeChecked();
 await consent.check();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 const fits=await page.locator(".consent-card .business-check").evaluate(label=>{const bounds=label.getBoundingClientRect();const span=label.querySelector("span")!.getBoundingClientRect();return span.right<=bounds.right+1&&span.left>=bounds.left});
 expect(fits).toBe(true);
 await page.screenshot({path:"test-results/consent-mobile.png",fullPage:true});
 await page.getByRole("button",{name:"Save business details",exact:true}).click();
 await expect(page.getByRole("status")).toContainText("Business details saved");
 await page.getByRole("tab",{name:"Activity",exact:true}).click();
 await page.getByRole("button",{name:"Start new research",exact:true}).click();
 await nav.getByRole("button",{name:"Dashboard",exact:true}).click();
 await page.getByRole("button",{name:"View research progress"}).click();
 const progress=page.getByRole("dialog",{name:"Website research"});
 await expect(progress).toBeVisible();
 await expect(progress.getByRole("heading",{name:/Reviewing your key pages|Research complete|Research saved with gaps/})).toBeVisible();
 await expect(progress.getByText(/pages · .*previews saved/)).toBeVisible();
 await page.screenshot({path:"test-results/research-progress-modal.png"});
 await progress.getByRole("button",{name:"Close",exact:true}).click();
 await expect(progress).not.toBeVisible();
});

test("dashboard document parser and image editor run locally in dedicated modals",async({page})=>{
 await accountAndWorkspace(page);
 const nav=page.getByRole("navigation",{name:"Main navigation"});
 await nav.getByRole("button",{name:"Dashboard",exact:true}).click();
 await openTool(page,"Document parser");
 const parser=page.getByRole("dialog",{name:"Document parser & converter"});
 await expect(parser).toBeVisible();
 await parser.getByLabel("Business document",{exact:true}).setInputFiles({name:"business.txt",mimeType:"text/plain",buffer:Buffer.from("Workshop services include custom components and owner-reviewed quotations.")});
 await parser.getByLabel("I am authorized to process this file",{exact:false}).check();
 await parser.getByLabel("I consent to sending the selected scanned PDF pages to Meta",{exact:false}).check();
 await parser.getByRole("button",{name:"Extract document batch"}).click();
 await expect(parser.getByText("Workshop services include custom components",{exact:false})).toBeVisible();
 const exported=page.waitForEvent("download");await parser.getByRole("button",{name:"Download Markdown"}).click();
 expect((await exported).suggestedFilename()).toBe("sentinelx-documents.md");
 await parser.getByRole("button",{name:"Close dialog"}).click();
 await openTool(page,"Image editor");
 const editor=page.getByRole("dialog",{name:"Image editor",exact:true});
 await editor.getByLabel("Image to edit").setInputFiles({name:"fixture.png",mimeType:"image/png",buffer:Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGOwiVoAAAIMATcAJ4DRAAAAAElFTkSuQmCC","base64")});
 await editor.getByLabel("I am authorized to process this file",{exact:false}).check();
 await editor.getByLabel("Width",{exact:true}).fill("200");await editor.getByLabel("Height",{exact:true}).fill("150");
 await editor.getByRole("button",{name:"Apply image edits"}).click();
 await expect(editor.getByRole("img",{name:"Saved business visual"})).toBeVisible();
 await editor.getByRole("button",{name:"Close dialog"}).click();
 await openTool(page,"Competitor research");
 const research=page.getByRole("dialog",{name:"Competitor research",exact:true});
 await expect(research.getByLabel("Use my saved business details",{exact:false})).toBeChecked();
 await research.getByLabel("Location",{exact:true}).fill("Kalyani");
 await research.getByLabel("Your prompt",{exact:true}).fill("Find comparable local wooden parts workshops.");
 await expect(research.getByRole("checkbox",{name:"Send this recording to Meta for transcription"})).toHaveCount(0);
 await expect(research.getByRole("button",{name:"Record voice prompt"})).toBeDisabled();
 await expect(research.locator(".voice-field-mic")).toHaveAttribute("title","Voice input requires live Meta transcription");
 await expect(research.getByRole("button",{name:"Start research",exact:true})).toBeDisabled();
 await expect(research.getByText("Live AI is not configured.",{exact:false})).toBeVisible();
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
 await page.getByRole("button",{name:"Evidence reports",exact:true}).click();
 await page.getByRole("button",{name:"Generate evidence-based draft"}).click();
 await expect(page.getByRole("heading",{name:"Offline fixture draft"})).toBeVisible();
 await page.getByRole("button",{name:"Settings",exact:true}).click();
 await page.getByRole("button",{name:"Sign out",exact:true}).last().click();
 await expect(page.getByRole("heading",{name:"Welcome back"})).toBeVisible();
});


test("legacy sample URL routes visitors to the real product",async({page})=>{
 await page.goto("/demo");
 await expect(page).toHaveURL(new RegExp("/$"));
 await expect(page.getByRole("heading",{name:"Welcome back"})).toBeVisible();
 await expect(page.getByText("Fictional demonstration workshop")).toHaveCount(0);
});

test("dashboard tools, modal edits, saved visuals, landing review and export",async({page})=>{
 await accountAndWorkspace(page);
 const navigation=page.getByRole("navigation",{name:"Main navigation"});
 await navigation.getByRole("button",{name:"Dashboard",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Your business workspace"})).toBeVisible();
  await page.getByRole("button",{name:"Browse business tools",exact:true}).click();
  await expect(page.locator(".tool-card")).toHaveCount(10);
 await page.screenshot({path:"test-results/dashboard-desktop.png",fullPage:true});
 await openTool(page,"Create campaign");
 await expect(page.getByRole("heading",{name:"Create a campaign"})).toBeVisible();
 await expect(page.getByLabel("What do you offer?")).toHaveCount(0);
 await expect(page.getByLabel("Business name",{exact:true})).toHaveCount(0);
 await page.getByRole("textbox",{name:"Campaign requirements",exact:true}).fill("Focus on custom woodworking quotations, showing the design and quantity needed for a complete inquiry.");
 await page.getByRole("combobox",{name:"Campaign goal",exact:true}).selectOption("Generate qualified inquiries");
 await expect(page.getByRole("checkbox",{name:"Send this recording to Meta for transcription"})).toHaveCount(0);
 await expect(page.getByRole("dialog",{name:"Create a campaign",exact:true}).getByRole("button",{name:"Record voice prompt",exact:true})).toBeDisabled();
 const platforms=page.getByRole("group",{name:"Where will you share it?"});
 for(const platform of ["LinkedIn","X (Twitter)","Google Business Profile","YouTube","Blogger"])await expect(platforms.getByLabel(platform,{exact:true})).toBeVisible();
 await page.getByText("Generation options",{exact:true}).click();
 await page.getByLabel("Use sample data (no credits)").check();
 await page.getByRole("button",{name:"Create sample campaign",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Campaign calendar",exact:true})).toBeVisible();
 const sheet=page.locator(".campaign-sheet");
 await expect(sheet.locator("tbody tr")).toHaveCount(7);
 await expect(sheet.locator("thead th")).toHaveText(["Day / status","Platform","Format","Caption","Hashtags","Call to action","Image guidance","Image prompt","Reel / video script","Saved visual","Actions"]);
 async function expectAlignedColumns(){
  const aligned=await sheet.evaluate(table=>{
   const headers=Array.from(table.querySelectorAll("thead th"));
   const rows=Array.from(table.querySelectorAll("tbody tr"));
   return rows.every(row=>getComputedStyle(row).display==="table-row"&&row.children.length===headers.length&&Array.from(row.children).every((cell,index)=>{
    const heading=headers[index].getBoundingClientRect();const bounds=cell.getBoundingClientRect();
    return getComputedStyle(cell).display==="table-cell"&&Math.abs(bounds.left-heading.left)<2&&Math.abs(bounds.width-heading.width)<2;
   }));
  });
  expect(aligned).toBe(true);
 }
 await expectAlignedColumns();
 await page.screenshot({path:"test-results/campaign-sheet-columns-desktop.png",fullPage:true});
 await page.setViewportSize({width:390,height:844});await expectAlignedColumns();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 const scrollable=await page.locator(".campaign-table-scroll").evaluate(element=>{element.scrollLeft=element.scrollWidth;return element.scrollLeft>0});
 expect(scrollable).toBe(true);
 await page.locator(".campaign-table-scroll").evaluate(element=>{element.scrollLeft=0});
 await page.setViewportSize({width:1280,height:900});
 await page.getByRole("button",{name:"Edit day 1 post",exact:true}).click();
 const edit=page.getByRole("dialog",{name:"Edit day 1 post"});
 await expect(edit).toBeVisible();
 await expect(edit.getByLabel("Image prompt")).toBeVisible();
 await expect(edit.getByLabel(/Reel \/ video script/)).toBeVisible();
 await edit.getByRole("textbox",{name:"Caption",exact:true}).fill("A saved edit to the sample campaign caption, ready for owner review.");
 await edit.getByLabel(/Hashtags/).fill("#Woodcraft\n#CustomFurniture #Design, #Joinery");
 await edit.getByRole("textbox",{name:"Image prompt",exact:true}).fill("Use only the owner-approved wooden furniture photo in a clear workshop setting.");
 await edit.getByRole("button",{name:"Save post",exact:true}).click();
 await expect(edit).not.toBeVisible();
 await expect(page.getByText("A saved edit to the sample campaign caption, ready for owner review.",{exact:true})).toBeVisible();
 const firstRow=sheet.locator("tbody tr").first();
 await expect(firstRow.locator("td").nth(3)).toHaveText("A saved edit to the sample campaign caption, ready for owner review.");
 await expect(firstRow.locator("td").nth(4)).toHaveText("#Woodcraft #CustomFurniture #Design #Joinery");
 await expect(firstRow.locator("td").nth(7)).toHaveText("Use only the owner-approved wooden furniture photo in a clear workshop setting.");
 await page.getByRole("button",{name:"Edit day 1 post",exact:true}).click();
 await page.keyboard.press("Escape");
 await expect(edit).not.toBeVisible();
 await page.getByRole("button",{name:"Create or view visuals"}).first().click();
 await page.getByRole("button",{name:"Generate visuals",exact:true}).click();
 await expect(page.locator(".visual-card")).toHaveCount(1);
 const days=page.getByLabel("Choose campaign day");
 const dayOne=await days.inputValue();
 const dayTwo=await days.locator("option").nth(1).getAttribute("value");
 await days.selectOption(dayTwo!);
 await expect(page.locator(".visual-card")).toHaveCount(0);
 await days.selectOption(dayOne);
 await expect(page.locator(".visual-card img")).toBeVisible();
 await navigation.getByRole("button",{name:"Landing pages",exact:true}).click();
 await page.getByRole("button",{name:"Generate page draft",exact:true}).click();
 await expect(page.locator("iframe[title='Landing preview']")).toBeVisible();
 await page.getByRole("button",{name:"Edit copy",exact:true}).click();
 const copy=page.getByRole("dialog",{name:"Edit landing page copy"});
 await copy.getByRole("textbox",{name:"Headline",exact:true}).fill("A clearly edited landing page for our custom furniture workshop");
 await copy.getByRole("button",{name:"Save changes",exact:true}).click();
 await expect(copy).not.toBeVisible();
 await page.getByRole("button",{name:"Review before publishing",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Review & export",exact:true})).toBeVisible();
 const landing=page.locator(".review-list-row").filter({hasText:"LANDING PAGE"}).first();
 await landing.getByRole("button",{name:"Review",exact:true}).click();
 const review=page.getByRole("dialog",{name:"Review deliverable"});
 await review.getByRole("button",{name:"Approve deliverable",exact:true}).click();
 await expect(review).not.toBeVisible();
 await expect(page.getByText(/Decision approved recorded/)).toBeVisible();
 await navigation.getByRole("button",{name:"Landing pages",exact:true}).click();
 await page.getByRole("button",{name:"Publish page",exact:true}).click();
 const publicPath=page.getByRole("link",{name:"Open public page",exact:true});
 await expect(publicPath).toBeVisible();
 const publicPage=await page.context().newPage();
 await publicPage.goto((await publicPath.getAttribute("href"))!);
 await expect(publicPage.getByRole("heading",{name:"A clearly edited landing page for our custom furniture workshop"})).toBeVisible();
 await publicPage.close();
 await navigation.getByRole("button",{name:"Review & export",exact:true}).click();
 const promise=page.waitForEvent("download");
 await page.getByRole("button",{name:"Download approved pack",exact:true}).click();
 expect((await promise).suggestedFilename()).toBe("sentinelx-approved-pack.zip");
 await page.reload();
 await expect(page.getByRole("heading",{name:"Review & export",exact:true})).toBeVisible();
 await navigation.getByRole("button",{name:"Dashboard",exact:true}).click();
 // This request stub is explicit offline test data; the product keeps live mode as its default.
 await page.route("**/api/v1/campaigns/runtime",route=>route.fulfill({json:{mode:"sample",is_guest:false,live_enabled:false,message:"Offline browser test fixture"}}));
 await openTool(page,"Review a photo");
 await page.getByLabel("Upload a product photo").setInputFiles({name:"fixture-product.png",mimeType:"image/png",buffer:Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGOwiVoAAAIMATcAJ4DRAAAAAElFTkSuQmCC","base64")});
 await page.getByRole("button",{name:"Analyze photo",exact:true}).click();
 await expect(page.locator(".photo-result").getByText("fixture-product.png",{exact:true})).toBeVisible();
 await page.getByRole("dialog",{name:"Photo review",exact:true}).getByRole("button",{name:"Close dialog",exact:true}).click();
 await page.setViewportSize({width:390,height:844});
 await expect(page.getByRole("heading",{name:"Your business workspace"})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:"test-results/dashboard-mobile.png",fullPage:true});
 await navigation.getByRole("button",{name:"Campaigns",exact:true}).click();
 await expect(page.locator(".campaign-sheet tbody tr")).toHaveCount(7);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:"test-results/campaign-mobile.png",fullPage:true});
});

test("campaign duration and tone create complete 10 and 30 day sheets using the saved profile",async({page})=>{
 await accountAndWorkspace(page);
 const navigation=page.getByRole("navigation",{name:"Main navigation"});
 for(const days of [10,30]){
  await navigation.getByRole("button",{name:"Dashboard",exact:true}).click();
  await openTool(page,"Create campaign");
  await expect(page.getByLabel("What do you offer?")).toHaveCount(0);
  await page.getByRole("combobox",{name:"Campaign duration",exact:true}).selectOption(String(days));
  await page.getByRole("combobox",{name:"Campaign tone",exact:true}).selectOption("friendly");
  await page.getByRole("textbox",{name:"Campaign requirements",exact:true}).fill(`Create a ${days} day campaign explaining custom trade inquiries and the design information needed.`);
  await page.getByText("Generation options",{exact:true}).click();await page.getByLabel("Use sample data (no credits)").check();
  await page.getByRole("button",{name:"Create sample campaign",exact:true}).click();
  await expect(page.getByText(`${days}-day content plan`,{exact:true})).toBeVisible();
  await expect(page.locator(".campaign-sheet tbody tr")).toHaveCount(days);
  await expect(page.locator(".campaign-sheet tbody tr").last().locator("td").first()).toContainText(`Day ${days}`);
 }
 await page.route("**/api/v1/campaigns/runtime",route=>route.fulfill({json:{mode:"live",is_guest:false,live_enabled:true,message:"Mock live test"}}));
 await page.reload();await expect(page.locator(".campaign-sheet tbody tr")).toHaveCount(30);
 await expect(page.getByRole("status").filter({hasText:"generic sample fixtures"})).toBeVisible();
 await page.getByRole("button",{name:"Create a business-specific AI campaign",exact:true}).click();
 await expect(page.getByRole("button",{name:"Generate campaign",exact:true})).toBeVisible();
 await page.getByText("Generation options",{exact:true}).click();
 await expect(page.getByLabel("Use sample data (no credits)")).not.toBeChecked();
 await page.getByRole("textbox",{name:"Campaign requirements",exact:true}).fill("Show our custom woodwork for trade customers, using the saved business profile.");
 let generationMode="";
 await page.route("**/api/v1/campaigns",async route=>{
  if(route.request().method()!=="POST")return route.continue();
  generationMode=route.request().postDataJSON().generation_mode;
  await route.fulfill({status:503,json:{detail:"Live Meta unavailable. No sample was substituted."}});
 });
 await page.getByRole("button",{name:"Generate campaign",exact:true}).click();
 await expect(page.getByText("Live Meta unavailable. No sample was substituted.",{exact:true})).toBeVisible();
 expect(generationMode).toBe("live");
 await expect(page.getByRole("heading",{name:"Create a campaign",exact:true})).toBeVisible();
});

test("campaign mic requests permission directly and inserts an editable Meta transcript without submitting",async({page})=>{
 await accountAndWorkspace(page);
 await page.route("**/api/v1/campaigns/runtime",route=>route.fulfill({json:{mode:"live",live_enabled:true,is_guest:false,message:"Mock live test"}}));
 await page.addInitScript(()=>{
  navigator.mediaDevices.getUserMedia=async()=>{const context=new AudioContext();const oscillator=context.createOscillator();const destination=context.createMediaStreamDestination();oscillator.connect(destination);oscillator.start();return destination.stream};
 });
 await page.reload();
 const calls:Buffer[]=[];let campaigns=0;
 page.on("request",request=>{if(request.method()==="POST"&&request.url().endsWith("/api/v1/campaigns"))campaigns++});
 await page.route("**/api/v1/prompts/transcribe",async route=>{calls.push(route.request().postDataBuffer()!);await route.fulfill({json:{provenance:"live_meta",model:"mock-voice",transcript:"Show the custom inquiry process with product examples."}})});
 await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Dashboard",exact:true}).click();
 await openTool(page,"Create campaign");
 await page.getByRole("textbox",{name:"Campaign requirements",exact:true}).fill("Focus on trade buyers.");
 await expect(page.getByRole("checkbox",{name:/Send this recording/})).toHaveCount(0);
 const embedded=page.locator(".voice-field").filter({has:page.getByRole("textbox",{name:"Campaign requirements",exact:true})});
 const bounds=await embedded.evaluate(element=>{const input=element.querySelector("textarea")!.getBoundingClientRect();const mic=element.querySelector("button")!.getBoundingClientRect();return mic.left>=input.left&&mic.right<=input.right&&mic.top>=input.top&&mic.bottom<=input.bottom});
 expect(bounds).toBe(true);
 await page.getByRole("dialog",{name:"Create a campaign",exact:true}).getByRole("button",{name:"Record voice prompt",exact:true}).click();
 await expect(page.getByRole("button",{name:"Stop and transcribe voice prompt",exact:true})).toBeVisible();
 await page.getByRole("textbox",{name:"Campaign requirements",exact:true}).fill("Focus on trade buyers. Keep this latest typed note.");
 await expect(page.getByRole("button",{name:"Generate campaign",exact:true})).toBeDisabled();
 // Synthetic audio must have enough duration to satisfy the real WAV intake bound.
 await page.waitForTimeout(900);
 await page.getByRole("button",{name:"Stop and transcribe voice prompt",exact:true}).click();
 await expect(page.getByRole("textbox",{name:"Campaign requirements",exact:true})).toHaveValue("Focus on trade buyers. Keep this latest typed note. Show the custom inquiry process with product examples.");
 expect(calls).toHaveLength(1);expect(calls[0].includes(Buffer.from("RIFF"))).toBe(true);expect(calls[0].includes(Buffer.from('name="request_id"'))).toBe(true);expect(campaigns).toBe(0);
 await page.screenshot({path:"test-results/campaign-requirements-mic.png",fullPage:true});
});

test("campaign mic permission denial preserves typed requirements and makes no transcription request",async({page})=>{
 await accountAndWorkspace(page);
 await page.route("**/api/v1/campaigns/runtime",route=>route.fulfill({json:{mode:"live",live_enabled:true,is_guest:false,message:"Mock live test"}}));
 await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException("Denied","NotAllowedError")}});
 await page.reload();let calls=0;page.on("request",r=>{if(r.url().endsWith("/api/v1/prompts/transcribe"))calls++});
 await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Dashboard",exact:true}).click();
 await openTool(page,"Create campaign");
 await page.getByRole("textbox",{name:"Campaign requirements",exact:true}).fill("Keep my typed campaign requirements.");
 await page.getByRole("dialog",{name:"Create a campaign",exact:true}).getByRole("button",{name:"Record voice prompt",exact:true}).click();
 await expect(page.locator(".prompt-voice").getByRole("alert")).toContainText("Microphone access was denied");
 await expect(page.getByRole("textbox",{name:"Campaign requirements",exact:true})).toHaveValue("Keep my typed campaign requirements.");expect(calls).toBe(0);
});

test("business mission entry points are removed from the workspace",async({page})=>{
 await accountAndWorkspace(page);
 const nav=page.getByRole("navigation",{name:"Main navigation"});
 await expect(nav.getByRole("button",{name:"Business engine",exact:true})).toHaveCount(0);
 await expect(page.getByRole("button",{name:"Start business mission",exact:true})).toHaveCount(0);
 await expect(page.getByRole("button",{name:"Run a business mission",exact:true})).toHaveCount(0);
 await expect(page.getByRole("button",{name:"Analyze website",exact:true})).toHaveCount(0);
 await page.evaluate(()=>{window.location.hash="mission"});
 await expect(page).toHaveURL(/#dashboard$/);
 await expect(page.getByRole("heading",{name:"Your business workspace",exact:true})).toBeVisible();
});


test("failed social synthesis exposes saved evidence and distinguishes completed searches from a report",async({page})=>{
 await accountAndWorkspace(page);
 const job={id:"failed-social-report",state:"partial",created_at:"2026-10-30T10:00:00Z",input_profile:{name:"Browser workshop",socials:[]},report:{pages:[],remaining_urls:[],activity:[],limitations:[],coverage:{pages_collected:0,screenshots_saved:0},insights:null,visual_review:null,social_research:{status:"failed",stage:"validation",error:"A social finding could not be matched to the correct saved source or account.",attempts:[{platform:"instagram",url:"https://instagram.com/workshop",status:"completed"}],sources:[{id:"S1.W1",url:"https://instagram.com/workshop",text:"Custom wooden parts in Kalyani.",origin:"search_pointer"}]}}};
 await page.route("**/business-profile/research",route=>route.fulfill({json:[job]}));
 await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Business & research",exact:true}).click();
 await page.reload();await page.getByRole("tab",{name:"Social insights",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Social research needs attention",exact:true})).toBeVisible();
 await expect(page.getByText("Report stage: validation",{exact:true})).toBeVisible();
 await page.getByText("View saved social evidence (1)",{exact:true}).click();
 await expect(page.getByText("Custom wooden parts in Kalyani.",{exact:true})).toBeVisible();
 await expect(page.getByRole("link",{name:"Open source",exact:true})).toHaveAttribute("href","https://instagram.com/workshop");
 await expect(page.getByRole("heading",{name:"Instagram improvement report",exact:true})).toHaveCount(0);
});


test("document parser explains non-JSON upload rejection and retries the same file explicitly",async({page})=>{
 await accountAndWorkspace(page);
 await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Dashboard",exact:true}).click();
 await openTool(page,"Document parser");
 const parser=page.getByRole("dialog",{name:"Document parser & converter"});
 await parser.getByLabel("Business document",{exact:true}).setInputFiles({name:"notes.txt",mimeType:"text/plain",buffer:Buffer.from("Useful business document notes.")});
 await parser.getByLabel("I am authorized to process this file",{exact:false}).check();
 await parser.getByLabel("I consent to sending the selected scanned PDF pages to Meta",{exact:false}).check();
 await expect(parser.getByLabel("Use Meta AI to read scanned PDF pages",{exact:false})).toBeChecked();
 const ids:string[]=[];let attempts=0;
 await page.route("**/api/v1/workbench/documents",async route=>{
  const body=route.request().postDataBuffer()!.toString();
  ids.push(body.match(/name="request_id"\r\n\r\n([^\r]+)/)![1]);
  attempts++;
  if(attempts===1)return route.fulfill({status:413,contentType:"text/html",body:"<h1>Request Entity Too Large</h1>"});
  return route.continue();
 });
 await parser.getByRole("button",{name:"Extract document batch",exact:true}).click();
 await expect(parser.getByRole("alert")).toContainText("upload was rejected because it is too large");
 await expect(parser.getByRole("alert")).not.toContainText("JSON");
 await parser.getByRole("button",{name:"Extract document batch",exact:true}).click();
 await expect(parser.getByText("Useful business document notes.",{exact:true})).toBeVisible();
 expect(ids).toHaveLength(2);expect(ids[0]).not.toBe(ids[1]);
});


test("scanned document results distinguish OCR text from unreadable pages",async({page})=>{
 await accountAndWorkspace(page);
 await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Dashboard",exact:true}).click();
 await openTool(page,"Document parser");
 const parser=page.getByRole("dialog",{name:"Document parser & converter"});
 await parser.getByLabel("Business document",{exact:true}).setInputFiles({name:"scan.pdf",mimeType:"application/pdf",buffer:Buffer.from("synthetic PDF upload fixture; endpoint stubbed")});
 await parser.getByLabel("I am authorized to process this file",{exact:false}).check();
 await parser.getByLabel("I consent to sending the selected scanned PDF pages to Meta",{exact:false}).check();
 await page.route("**/api/v1/workbench/documents",async route=>{
  const body=route.request().postDataBuffer()!.toString();
  expect(body).toContain('name="use_meta"\r\n\r\ntrue');
  await route.fulfill({status:201,json:{id:"ocr-result",tool:"documents",status:"completed",provenance:"user_supplied",data:{total_pages:2,next_page:null,pages:[{page:1,text:"Workshop order notes transcribed for review.",needs_ocr:false,truncated:false,extraction_method:"meta_pdf"},{page:2,text:"",needs_ocr:true,truncated:false,ocr_error:"Meta could not read this page; try a clearer scan."}]}}});
 });
 await parser.getByRole("button",{name:"Extract document batch",exact:true}).click();
 await expect(parser.getByText(/1 of 2 pages \/ chunks contain text/)).toBeVisible();
 await parser.getByText("Page / chunk 1",{exact:false}).click();
 await expect(parser.getByText("Workshop order notes transcribed for review.",{exact:true})).toBeVisible();
 await expect(parser.getByText("Page / chunk 1",{exact:false})).toContainText("Meta AI transcription (verify against original)");
 await parser.getByText("Page / chunk 2",{exact:false}).click();
 await expect(parser.getByText("Enable Meta PDF reading with consent",{exact:false})).toBeVisible();
});


test("competitor and keyword tools submit distinct briefs and reopen source-linked results without another search",async({page})=>{
 await accountAndWorkspace(page);
 await page.route("**/api/v1/campaigns/runtime",route=>route.fulfill({json:{live_enabled:true}}));
 const rows:Record<string,unknown>[]=[];const calls:Record<string,unknown>[]=[];
 await page.route("**/api/v1/workbench**",async route=>{
  if(route.request().method()==="GET")return route.fulfill({json:rows});
  const body=route.request().postDataJSON();calls.push(body);
  const row={id:body.request_id,tool:body.tool,prompt:body.prompt,status:"completed",provenance:"live_meta",model:"offline-test",data:{summary:`Saved ${body.tool} research for trade wood components.`,citations:[{url:"https://example.org/research",title:"Research source"}],limitation:"Public source pointers; popularity and proximity remain unverified."}};
  rows.push(row);await route.fulfill({status:201,json:row});
 });
 const nav=page.getByRole("navigation",{name:"Main navigation"});
 await nav.getByRole("button",{name:"Dashboard",exact:true}).click();
 for(const item of [{tool:"competitors",title:"Competitor research",card:"Competitor research"},{tool:"keywords",title:"SEO keyword researcher",card:"SEO keywords & hashtags"}]){
  await openTool(page,item.card);
  const dialog=page.getByRole("dialog",{name:item.title,exact:true});
  await dialog.getByRole("textbox",{name:"Your prompt",exact:true}).fill(`Research ${item.tool} for trade wood components; exclude retail furniture shops.`);
  await dialog.getByRole("textbox",{name:"Location",exact:true}).fill("Kalyani");
  await dialog.getByRole("button",{name:"Start research",exact:true}).click();
  await expect(dialog.getByText(`Saved ${item.tool} research for trade wood components.`,{exact:true})).toBeVisible();
  await expect(dialog.getByRole("link",{name:"Research source",exact:true})).toHaveAttribute("href","https://example.org/research");
  expect(calls.at(-1)?.tool).toBe(item.tool);expect(calls.at(-1)?.location).toBe("Kalyani");expect(calls.at(-1)?.use_business).toBe(true);
  await dialog.getByRole("button",{name:"Close dialog",exact:true}).click();
  await openTool(page,item.card);
  const reopened=page.getByRole("dialog",{name:item.title,exact:true});
  await reopened.getByRole("combobox",{name:"Saved tool results",exact:true}).selectOption(String(calls.at(-1)?.request_id));
  await expect(reopened.getByText(`Saved ${item.tool} research for trade wood components.`,{exact:true})).toBeVisible();
  await reopened.getByRole("button",{name:"Close dialog",exact:true}).click();
 }
 expect(calls).toHaveLength(2);
});


test("AI research results render readable sections tables emphasis and safe links on desktop and phone",async({page})=>{
 await accountAndWorkspace(page);
 await page.route("**/api/v1/campaigns/runtime",route=>route.fulfill({json:{live_enabled:true}}));
 let generated=0;
 const summary="## Opportunities worth reviewing\n\nPrioritize **qualified trade inquiries**, using the evidence below.\n\n- Explain the minimum order clearly.\n- Invite a drawing and quantity.\n\n### Search intent\n\n| Phrase | Intent |\n| --- | --- |\n| Custom wooden parts | Trade inquiry |\n\n> These are ideas to test, not measured growth.\n\n[Evidence link](https://example.org/evidence)\n\n[Unsafe link](javascript:alert%281%29)\n\n<script>window.aiInjected=true</script>\n\n![Remote image](https://example.org/tracking.png)";
 await page.route("**/api/v1/workbench",route=>{
  generated++;
  return route.fulfill({status:201,json:{id:"formatted-report",tool:"keywords",status:"completed",provenance:"live_meta",model:"offline-test",data:{summary,citations:[{title:"Public research source",url:"https://example.org/evidence"}],limitation:"Keyword volume is unmeasured."}}});
 });
 await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Dashboard",exact:true}).click();
 await openTool(page,"SEO keywords & hashtags");
 const dialog=page.getByRole("dialog",{name:"SEO keyword researcher",exact:true});
 await dialog.getByRole("textbox",{name:"Your prompt",exact:true}).fill("Find trade inquiry keyword opportunities for custom wooden components.");
 await dialog.getByRole("button",{name:"Start research",exact:true}).click();
 await expect(dialog.getByRole("heading",{name:"Opportunities worth reviewing",exact:true})).toBeVisible();
 await expect(dialog.locator(".ai-prose strong")).toHaveText("qualified trade inquiries");
 await expect(dialog.getByRole("table")).toBeVisible();
 await expect(dialog.getByRole("columnheader",{name:"Intent",exact:true})).toBeVisible();
 await expect(dialog.getByRole("link",{name:"Public research source",exact:true})).toHaveAttribute("href","https://example.org/evidence");
 await expect(dialog.getByRole("link",{name:"Unsafe link",exact:true})).toHaveCount(0);
 await expect(dialog.getByRole("img",{name:"Remote image",exact:true})).toHaveCount(0);
 expect(await page.evaluate(()=>Boolean((window as unknown as Record<string,unknown>).aiInjected))).toBe(false);
 await page.screenshot({path:"test-results/ai-research-polished-desktop.png",fullPage:true});
 await page.setViewportSize({width:390,height:844});
 expect(await dialog.evaluate(element=>element.scrollWidth<=element.clientWidth+1)).toBe(true);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await dialog.locator(".workbench-output").scrollIntoViewIfNeeded();
 await page.screenshot({path:"test-results/ai-research-polished-mobile.png",fullPage:true});
 expect(generated).toBe(1);
});


test("post drafts visually separate captions hashtags scenes prompts and calls to action",async({page})=>{
 await accountAndWorkspace(page);
 await page.route("**/api/v1/campaigns/runtime",route=>route.fulfill({json:{live_enabled:true}}));
 await page.route("**/api/v1/workbench",route=>route.fulfill({status:201,json:{id:"formatted-post",tool:"post",status:"completed",provenance:"live_meta",model:"offline-test",data:{title:"Make your next trade inquiry count",caption:"Have a **custom wooden component** in mind?\nSend a drawing, quantity and preferred date so we can discuss your requirements.",hashtags:["#Woodworking","#TradeComponents","#CustomWoodwork"],image_prompt:"Show an owner-approved component in a clean workshop setting, with space for a short headline.",video_scenes:["Open with the product detail and a clear design reference.","Show the drawing, quantity and required date, then invite an inquiry."],call_to_action:"Send your drawing and quantity for review.",assumptions:["Owner must confirm product availability."]}}}));
 await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Dashboard",exact:true}).click();
 await openTool(page,"Post generator");
 const dialog=page.getByRole("dialog",{name:"Post generator",exact:true});
 await dialog.getByRole("textbox",{name:"Your prompt",exact:true}).fill("Explain the details trade customers should send with an inquiry.");
 await dialog.getByRole("button",{name:"Generate",exact:true}).click();
 await expect(dialog.locator(".ai-caption-card strong")).toHaveText("custom wooden component");
 await expect(dialog.locator(".ai-hashtag-list span")).toHaveText(["#Woodworking","#TradeComponents","#CustomWoodwork"]);
 await expect(dialog.locator(".ai-scene-list li")).toHaveCount(2);
 await expect(dialog.locator(".ai-cta-card")).toContainText("Send your drawing and quantity");
 await expect(dialog.locator(".ai-brief-card")).toContainText("owner-approved component");
 await page.screenshot({path:"test-results/ai-post-polished-desktop.png",fullPage:true});
});


test("campaign history editable visual handoff bulk generation final approval and downloads persist",async({page})=>{
 test.setTimeout(120000);
 await accountAndWorkspace(page);
 const nav=page.getByRole("navigation",{name:"Main navigation"});
 async function createCampaign(requirements:string){
  await nav.getByRole("button",{name:"Dashboard",exact:true}).click();
  await openTool(page,"Create campaign");
  const modal=page.getByRole("dialog",{name:"Create a campaign",exact:true});
  await modal.getByRole("textbox",{name:"Campaign requirements",exact:true}).fill(requirements);
  await modal.getByText("Generation options",{exact:true}).click();
  await modal.getByLabel("Use sample data (no credits)").check();
  await modal.getByRole("button",{name:"Create sample campaign",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Campaign calendar",exact:true})).toBeVisible();
  return page.getByRole("combobox",{name:"Campaign history",exact:true}).inputValue();
 }
 const first=await createCampaign("Explain trade order requirements for custom wood components.");
 const second=await createCampaign("Prepare a distinct campaign introducing custom turning and bulk inquiries.");
 expect(first).not.toBe(second);
 const history=page.getByRole("combobox",{name:"Campaign history",exact:true});
 await expect(history.locator("option")).toHaveCount(2);
 await history.selectOption(first);
 await page.reload();await expect(history).toHaveValue(first);
 const sheet=page.locator(".campaign-sheet");
 await sheet.locator("tbody tr").nth(1).getByRole("button",{name:"Create or view visuals",exact:true}).click();
 const prompt=page.getByRole("textbox",{name:"Image generation prompt",exact:true});
 await expect(prompt).toHaveValue(/day 2/);
 await prompt.fill("Use an owner-approved wooden component, clean workshop lighting and a neutral background.");
 await page.getByRole("button",{name:"Generate visuals",exact:true}).click();
 await expect(page.locator(".visual-card img")).toBeVisible();
 await page.getByRole("button",{name:"Use this concept",exact:true}).click();
 await nav.getByRole("button",{name:"Campaigns",exact:true}).click();
 await expect(sheet.locator("tbody tr").nth(1).locator("td").nth(7)).toContainText("owner-approved wooden component, clean workshop lighting");
 await page.getByRole("button",{name:"Generate all missing visuals",exact:true}).click();
 const batch=page.getByRole("dialog",{name:"Generate campaign visuals",exact:true});
 await expect(batch.getByRole("button",{name:"Generate and save draft visuals",exact:true})).toBeDisabled();
 await batch.getByLabel("I want to generate the missing visuals",{exact:false}).check();
 await batch.getByRole("button",{name:"Generate and save draft visuals",exact:true}).click();
 await expect(page.getByText("7/7 processed",{exact:false})).toContainText("completed",{timeout:60000});
 await expect(sheet.locator("img")).toHaveCount(7);
 await page.reload();await expect(history).toHaveValue(first);await expect(sheet.locator("img")).toHaveCount(7);
 await page.getByRole("button",{name:"Review & finalize campaign",exact:true}).click();
 const review=page.getByRole("dialog",{name:"Final campaign review",exact:true});
 await expect(review.locator(".campaign-final-review article")).toHaveCount(7);
 await expect(review.getByRole("button",{name:"Approve and save final campaign",exact:true})).toBeDisabled();
 await review.getByLabel("I reviewed all posts and selected images",{exact:false}).check();
 await review.getByRole("button",{name:"Approve and save final campaign",exact:true}).click();
 await expect(page.getByText("Final campaign saved",{exact:true})).toBeVisible();
 for(const name of ["Download JSON","Download CSV","Download Excel","Download posts + images"])await expect(page.getByRole("button",{name,exact:true})).toBeVisible();
 const jsonDownload=page.waitForEvent("download");await page.getByRole("button",{name:"Download JSON",exact:true}).click();
 const artifact=await jsonDownload;const stream=await artifact.createReadStream();const chunks=[];for await(const chunk of stream!)chunks.push(chunk);
 const final=JSON.parse(Buffer.concat(chunks).toString());
 expect(final.manifest.campaign_id).toBe(first);expect(final.manifest.posts).toHaveLength(7);expect(final.manifest.externally_published).toBe(false);
 const excelDownload=page.waitForEvent("download");await page.getByRole("button",{name:"Download Excel",exact:true}).click();
 expect((await excelDownload).suggestedFilename()).toBe("sentinelx-final-campaign.xlsx");
 await page.screenshot({path:"test-results/campaign-final-delivery.png",fullPage:true});
 await page.reload();await expect(page.getByText("Final campaign saved",{exact:true})).toBeVisible();await expect(history.locator("option")).toHaveCount(2);
 await history.selectOption(second);await expect(sheet.locator("tbody tr")).toHaveCount(7);await expect(sheet.locator("img")).toHaveCount(0);
});


test("business chat keeps the dashboard clean opens tools from plus and restores conversations",async({page})=>{
 await accountAndWorkspace(page);
 await page.route("**/api/v1/campaigns/runtime",route=>route.fulfill({json:{mode:"live",live_enabled:true,is_guest:false}}));
 const saved:Record<string,unknown>[]=[];const requests:Record<string,unknown>[]=[];
 await page.route("**/api/v1/business-chat**",async route=>{
  const url=new URL(route.request().url());
  if(route.request().method()==="GET"){
   if(url.pathname.endsWith("/threads"))return route.fulfill({json:saved.map(row=>({id:row.thread_id,title:row.message}))});
   return route.fulfill({json:saved.filter(row=>row.thread_id===url.searchParams.get("thread_id"))});
  }
  const body=route.request().postDataJSON();requests.push(body);
  const row={id:body.request_id,thread_id:body.thread_id,message:body.message,status:"completed",provenance:"live_meta",answer:"## Prioritize inquiry quality\nUse your saved business context to ask for **design, quantity and required date**.",citations:[{source_id:"B1",quote:"Browser workshop"}],sources:[{id:"B1",filename:"Business profile",origin:"user_supplied"}],analysis:null};saved.push(row);return route.fulfill({status:201,json:row});
 });
 await page.reload();await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Dashboard",exact:true}).click();
 await expect(page.getByRole("heading",{name:"What should we work on?",exact:true})).toBeVisible();
 await expect(page.locator(".tool-card")).toHaveCount(0);
 await page.locator(".chat-context-options summary").click();
 await page.getByRole("group",{name:"Advisor focus areas"}).getByRole("button",{name:"marketing",exact:true}).click();
 const question=page.getByRole("textbox",{name:"Message your business assistant",exact:true});
 await question.fill("How can we improve the quality of trade inquiries?");
 await page.getByRole("button",{name:"Send business message",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Prioritize inquiry quality",exact:true})).toBeVisible();
 expect(requests).toHaveLength(1);expect(requests[0].focus).toEqual(["strategy","marketing"]);expect(requests[0].use_knowledge).toBe(true);
 await page.reload();await expect(page.getByRole("heading",{name:"Prioritize inquiry quality",exact:true})).toBeVisible();
 await page.getByRole("button",{name:"Browse business tools",exact:true}).click();
 const picker=page.getByRole("dialog",{name:"Business tools",exact:true});await expect(picker.locator(".tool-card")).toHaveCount(10);
 await picker.locator(".tool-card").filter({hasText:"Post generator"}).click();
 const post=page.getByRole("dialog",{name:"Post generator",exact:true});
 const inside=await post.locator(".voice-field").evaluate(element=>{const input=element.querySelector("textarea")!.getBoundingClientRect();const mic=element.querySelector("button")!.getBoundingClientRect();return mic.top>=input.top&&mic.bottom<=input.bottom&&mic.left>=input.left&&mic.right<=input.right});
 expect(inside).toBe(true);await post.getByRole("button",{name:"Close dialog",exact:true}).click();
 expect(requests).toHaveLength(1);
 await page.screenshot({path:"test-results/business-chat-desktop.png",fullPage:true});
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:"test-results/business-chat-mobile.png",fullPage:true});
});


test("knowledge uploads profile sales locally and calculate real chart values without AI",async({page})=>{
 await accountAndWorkspace(page);
 await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Business & research",exact:true}).click();
 await page.getByLabel("I am authorized to provide these business materials.",{exact:false}).check();
 const saved=page.waitForResponse(response=>response.request().method()==="POST"&&response.url().endsWith("/api/v1/business-profile"));
 await page.getByRole("button",{name:"Save business details",exact:true}).click();
 expect((await saved).ok()).toBe(true);
 await page.getByRole("tab",{name:"Knowledge base",exact:true}).click();
 await page.getByLabel("Knowledge documents",{exact:true}).setInputFiles({name:"sales-2025.csv",mimeType:"text/csv",buffer:Buffer.from("Region,Sales\nNorth,100.10\nSouth,40.20\nNorth,80.30\n")});
 await expect(page.getByRole("button",{name:"Save to knowledge base",exact:true})).toBeDisabled();
 await page.getByLabel("I am authorized to store these documents",{exact:false}).check();
 await page.getByRole("button",{name:"Save to knowledge base",exact:true}).click();
 await expect(page.getByRole("heading",{name:"sales-2025.csv",exact:true})).toBeVisible();
 await page.getByRole("combobox",{name:"Saved dataset",exact:true}).selectOption({label:"sales-2025.csv"});
 await page.getByRole("combobox",{name:"Metric column",exact:true}).selectOption("Sales");
 await page.getByRole("combobox",{name:"Group by",exact:true}).selectOption("Region");
 await page.getByRole("button",{name:"Calculate locally",exact:true}).click();
 const result=page.getByRole("region",{name:"Locally calculated data result",exact:true});
 await expect(result.getByRole("cell",{name:"180.40",exact:true})).toBeVisible();
 await expect(result.getByRole("cell",{name:"40.20",exact:true})).toBeVisible();
 await expect(result.getByRole("img",{name:"Chart of locally calculated values",exact:true})).toBeVisible();
 await page.screenshot({path:"test-results/knowledge-data-analysis.png",fullPage:true});
 await page.reload();await page.getByRole("tab",{name:"Knowledge base",exact:true}).click();
 await expect(page.getByRole("heading",{name:"sales-2025.csv",exact:true})).toBeVisible();
});
