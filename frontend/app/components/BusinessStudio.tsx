"use client";
import {useEffect,useState} from "react";

const BASE=process.env.NEXT_PUBLIC_API_URL ?? "";
type Provenance="live_meta"|"sample"|"user_supplied";
type Img={id:string;filename:string;result:{local:{width:number;height:number;brightness:number;contrast:number;edge_variance:number;technical_readiness:number;dominant_colors:string[]};model?:{overall:number;issues:string[];fixes:string[]}|null;provenance:Provenance}};
type Item={id:string;day:number;platform:string;post_type:string;caption:string;hashtags:string[];cta:string;creative_brief:string;state:string;provenance:Provenance;unsupported_claims:string[]};
type Campaign={id:string;business_description:string;goal:string;language:string;provenance:Provenance;audit:{analysis:{offer_summary:string;audience_guess:string;gaps:{finding:string;assumption:boolean;evidence_id:string|null}[];positioning_angles:string[]};evidence:{id:string;text?:string;url?:string;type:string}[]};items:Item[]};
type Variant={id:string;selected:boolean;recommended:boolean;provenance:Provenance;mime:string;prompt:string;scores:{local:{technical_readiness:number};brief_match?:{brief_match:number}|null;final_score:number|null}};
type Page={id:string;campaign_id:string;slug:string;url:string;published:boolean;leads_count:number;provenance:Provenance;spec:{business_name:string;headline:string;subheadline:string;offer:string;cta_label:string;theme:string;accent_color:string;hero_image_variant_id:string|null;[key:string]:unknown}};
type Approval={id:string;target_kind:string;target_id:string;state:string;events:{decision:string;note:string;reviewer_id:string;at:string}[]};
type Lead={id:string;name:string;phone:string;message:string;created_at:string};
type Runtime={mode:"sample"|"live"|"unavailable";is_guest:boolean;message:string};
type SavedCampaign={id:string;goal:string;provenance:Provenance};
const steps=["Brief & photos","Business audit","7-day campaign","Creatives","Landing page","Approval & export"] as const;
const demoDescription="We build handcrafted solid wood furniture, custom cabinetry and made-to-measure interiors. Prospective clients can request a consultation and discuss their requirements.";
function Flag({value}:{value:string}){const real=value==="live_meta";return <span className={real?"studio-badge live":"studio-badge"}>{real?"Live Meta":value.replaceAll("_"," ")}</span>}

export default function BusinessStudio({token,workspace}:{token:string;workspace:string}){
 const [step,setStep]=useState(0);
 const [website,setWebsite]=useState("https://kamalwoodcraft.in");
 const [description,setDescription]=useState(demoDescription);
 const [businessName,setBusinessName]=useState("Kamal Woodcraft");
 const [goal,setGoal]=useState("Increase qualified customer inquiries for custom furniture");
 const [language,setLanguage]=useState<"en"|"bn"|"hi">("en");
 const [platforms,setPlatforms]=useState<string[]>(["instagram","facebook"]);
 const [file,setFile]=useState<File|null>(null);
 const [images,setImages]=useState<Img[]>([]);
 const [campaign,setCampaign]=useState<Campaign|null>(null);
 const [itemId,setItemId]=useState("");
 const [variants,setVariants]=useState<Variant[]>([]);
 const [variantImages,setVariantImages]=useState<Record<string,string>>({});
 const [selectedVariant,setSelectedVariant]=useState<string|null>(null);
 const [page,setPage]=useState<Page|null>(null);
 const [preview,setPreview]=useState("");
 const [leads,setLeads]=useState<Lead[]>([]);
 const [board,setBoard]=useState<Approval[]>([]);
 const [reviewNote,setReviewNote]=useState("");
 const [budget,setBudget]=useState<string>("");
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 const [notice,setNotice]=useState("");
 const [brandMood,setBrandMood]=useState("warm, contemporary and handcrafted");
 const [requestedVariants,setRequestedVariants]=useState(1);
 const [pageTheme,setPageTheme]=useState("warm");
 const [whatsapp,setWhatsapp]=useState("");
 const [runtime,setRuntime]=useState<Runtime|null>(null);
 const [savedCampaigns,setSavedCampaigns]=useState<SavedCampaign[]>([]);
 const [sampleMode,setSampleMode]=useState(false);
 const generationMode=sampleMode||runtime?.mode==="sample"?"sample":"live";
 async function api<T>(path:string,method="GET",body?:unknown):Promise<T>{
   const response=await fetch(BASE+path,{method,headers:{"Content-Type":"application/json",Authorization:"Bearer "+token},body:body===undefined?undefined:JSON.stringify(body),cache:"no-store"});
   const data=await response.json().catch(()=>({detail:"Unexpected response"}));
   if(!response.ok)throw new Error(typeof data.detail==="string"?data.detail:`Request failed (${response.status})`);
   return data as T;
 }
 async function action(fn:()=>Promise<void>){
   setBusy(true);setError("");setNotice("");
   try{await fn()}catch(e){setError(e instanceof Error?e.message:"Something went wrong")}
   finally{setBusy(false)}
 }
 useEffect(()=>{setStep(0);setImages([]);setCampaign(null);setVariants([]);setPage(null);setBoard([]);setSelectedVariant(null);},[workspace]);
 useEffect(()=>{
   let active=true;
   api<Runtime>("/api/v1/campaigns/runtime").then(r=>{if(active)setRuntime(r)}).catch(e=>{if(active)setError(String(e))});
   if(workspace)api<SavedCampaign[]>(`/api/v1/campaigns?workspace_id=${encodeURIComponent(workspace)}`).then(async rows=>{
     if(!active)return;setSavedCampaigns(rows);
     if(rows.length)await openCampaign(rows[0].id);
   }).catch(e=>{if(active)setError(String(e))});
   return()=>{active=false};
 },[token,workspace]);
 useEffect(()=>{if(token)api<{meta:{remaining_usd:number}}>("/api/v1/inference/budget").then(d=>setBudget(String(d.meta?.remaining_usd??"unavailable"))).catch(()=>setBudget("unavailable"));},[token]);
 useEffect(()=>()=>{Object.values(variantImages).forEach(x=>URL.revokeObjectURL(x))},[variantImages]);
 async function scorePhoto(){
   if(!file)return;
   await action(async()=>{
     const form=new FormData();form.append("workspace_id",workspace);form.append("business_context",description.slice(0,1500));form.append("file",file);
     form.append("generation_mode",generationMode);
     const response=await fetch(BASE+"/api/v1/images/score",{method:"POST",headers:{Authorization:"Bearer "+token},body:form});
     const result=await response.json();if(!response.ok)throw new Error(typeof result.detail==="string"?result.detail:"Image score failed");
     setImages(previous=>[...previous,result as Img]);setFile(null);
     setNotice("Image measured and saved. AI evaluation only appears when a real model runs.");
   });
 }
 async function generateCampaign(){
   await action(async()=>{
     if(generationMode==="live"&&(!runtime||runtime.mode==="unavailable"))throw new Error(runtime?.message||"Checking generation service. Try again shortly.");
     const c=await api<Campaign>("/api/v1/campaigns","POST",{
       workspace_id:workspace,website:website||undefined,business_description:description,goal,language,
       platforms,image_ids:images.map(x=>x.id),generation_mode:generationMode
     });
     setSavedCampaigns(old=>[{id:c.id,goal:c.goal,provenance:c.provenance},...old]);
     setCampaign(c);setItemId(c.items[0]?.id||"");setStep(1);
     setNotice(c.provenance==="live_meta"?"Live Meta audit generated; review every claim.":"Clearly labeled sample campaign generated without model charges.");
   });
 }
 async function openCampaign(id:string){
   const c=await api<Campaign>(`/api/v1/campaigns/${id}?workspace_id=${encodeURIComponent(workspace)}`);
   setCampaign(c);setItemId(c.items[0]?.id||"");setGoal(c.goal);setDescription(c.business_description);setVariants([]);setPage(null);setPreview("");setBoard([]);
   const pages=await api<Page[]>(`/api/v1/landing?workspace_id=${encodeURIComponent(workspace)}`);
   const existing=pages.find(p=>p.campaign_id===c.id);
   if(existing){setPage(existing);setBusinessName(existing.spec.business_name);await loadPreview(existing.id)}
   const first=c.items[0];
   if(first){const vs=await api<Variant[]>(`/api/v1/campaigns/${c.id}/items/${first.id}/creatives?workspace_id=${encodeURIComponent(workspace)}`);
     setVariants(vs);setSelectedVariant(vs.find(v=>v.selected)?.id||null);await fetchVariantImages(c.id,first.id,vs)}
 }
 async function updateItem(item:Item,key:"caption"|"cta"|"creative_brief",text:string){
   if(!campaign)return;
   await action(async()=>{
     const changed=await api<Item>(`/api/v1/campaigns/${campaign.id}/items/${item.id}?workspace_id=${encodeURIComponent(workspace)}`,"PATCH",{[key]:text});
     setCampaign(old=>old?{...old,items:old.items.map(i=>i.id===item.id?{...i,...changed}:i)}:old);
     setNotice("Edited copy saved. Provenance marked user supplied.");
   });
 }
 async function createVariants(){
   if(!campaign||!itemId)return;
   await action(async()=>{
     const result=await api<{variants:Variant[];partial:boolean;warning?:string}>(
        `/api/v1/campaigns/${campaign.id}/items/${itemId}/creatives?workspace_id=${encodeURIComponent(workspace)}`,"POST",
        {variants:requestedVariants,brand_mood:brandMood,generation_mode:generationMode});
     setVariants(result.variants);
     await fetchVariantImages(campaign.id,itemId,result.variants);
     if(result.partial)setNotice(result.warning||"Some variants were unavailable; previous results preserved.");
   });
 }
 async function fetchVariantImages(cid:string,iid:string,vs:Variant[]){
   const next:Record<string,string>={};
   await Promise.all(vs.map(async v=>{
     const res=await fetch(BASE+`/api/v1/campaigns/${cid}/items/${iid}/creatives/${v.id}/image?workspace_id=${encodeURIComponent(workspace)}`,
       {headers:{Authorization:"Bearer "+token}});
     if(res.ok)next[v.id]=URL.createObjectURL(await res.blob());
   }));
   setVariantImages(next);
 }
 async function pickVariant(v:Variant){
   if(!campaign)return;
   await action(async()=>{
     const result=await api<Variant>(`/api/v1/campaigns/${campaign.id}/items/${itemId}/creatives/${v.id}/select?workspace_id=${encodeURIComponent(workspace)}`,"POST");
     setSelectedVariant(result.id);
     setVariants(prev=>prev.map(x=>({...x,selected:x.id===result.id})));
     setNotice("Creative selected for review; nothing has been published.");
   });
 }
 async function createLanding(){
   if(!campaign)return;
   await action(async()=>{
     const result=await api<Page>("/api/v1/landing/generate","POST",{workspace_id:workspace,
       campaign_id:campaign.id,business_name:businessName,theme:pageTheme,
       whatsapp_number:whatsapp||null,hero_image_variant_id:selectedVariant||null,generation_mode:generationMode});
     setPage(result);await loadPreview(result.id);
     setNotice("Landing page created as an unpublished draft. Approval required.");
   });
 }
 async function loadPreview(pid=page?.id){
   if(!pid)return;
   const res=await fetch(BASE+`/api/v1/landing/${pid}/preview?workspace_id=${encodeURIComponent(workspace)}`,{
     headers:{Authorization:"Bearer "+token}});
   if(!res.ok)throw Error("Landing preview failed");setPreview(await res.text());
 }
 async function saveLandingText(field:"headline"|"subheadline"|"offer",value:string){
   if(!page)return;
   await action(async()=>{
     const updated=await api<Page>(`/api/v1/landing/${page.id}?workspace_id=${encodeURIComponent(workspace)}`,"PATCH",{
       spec:{...page.spec,[field]:value}});
     setPage(updated);await loadPreview(updated.id);setNotice("Landing draft updated; publication remains off until approved.");
   });
 }
 async function publish(value:boolean){
   if(!page)return;
   await action(async()=>{
     const updated=await api<Page>(`/api/v1/landing/${page.id}?workspace_id=${encodeURIComponent(workspace)}`,"PATCH",{published:value});
     setPage(updated);setNotice(value?"Page published on this application host.":"Page unpublished.");
   });
 }
 async function loadBoard(){
   if(!campaign)return;
   const records=await api<Approval[]>(`/api/v1/campaigns/${campaign.id}/board?workspace_id=${encodeURIComponent(workspace)}`);
   setBoard(records);
 }
 async function decide(approval:Approval,decision:"approved"|"rejected"|"reopen"){
   await action(async()=>{
     await api(`/api/v1/approvals/${approval.id}/decide?workspace_id=${encodeURIComponent(workspace)}`,"POST",
       {decision,note:reviewNote});
     await loadBoard();
     setNotice(`Decision ${decision} recorded; no external publishing performed.`);
   });
 }
 async function loadLeads(){
   if(!page)return;
   await action(async()=>setLeads(await api<Lead[]>(`/api/v1/landing/${page.id}/leads?workspace_id=${encodeURIComponent(workspace)}`)));
 }
 async function download(path:string,name:string){
   await action(async()=>{
     const res=await fetch(BASE+path,{headers:{Authorization:"Bearer "+token}});
     if(!res.ok)throw Error("Export unavailable");
     const url=URL.createObjectURL(await res.blob());
     const link=document.createElement("a");link.href=url;link.download=name;document.body.appendChild(link);
     link.click();link.remove();URL.revokeObjectURL(url);
     setNotice("Downloaded. Only approved campaign content is included in pack exports.");
   });
 }
 if(!workspace)return <section className="panel"><h2>Create or select a workspace to start Studio.</h2></section>;
 return <section className="studio">
   <div className={runtime?.mode==="live"?"alert":"alert error"} role="status"><b>{runtime?.mode==="live"?"Live Meta Studio":runtime?.mode==="sample"?"Sample guest workspace":"Generation setup"}</b> · {runtime?.message||"Checking the generation service…"}</div>
   {runtime&&!runtime.is_guest&&<label className="studio-choice"><input type="checkbox" checked={sampleMode} onChange={e=>setSampleMode(e.target.checked)}/>Use sample data (no credits)</label>}
   {savedCampaigns.length>0&&<label>Saved campaigns<select aria-label="Saved campaigns" value={campaign?.id||""} onChange={e=>action(()=>openCampaign(e.target.value))}>{savedCampaigns.map(c=><option key={c.id} value={c.id}>{c.goal} · {c.provenance==="live_meta"?"Live Meta":"Sample"}</option>)}</select></label>}
   <div className="studio-heading"><div><span className="eyebrow">SENTINELX / BUSINESS STUDIO</span><h1>From business insight to launch-ready assets.</h1><p className="muted">Analyze evidence, improve product imagery, plan seven days, design an offer, and approve what leaves your workspace.</p></div><div className="studio-credit">App budget remaining <strong>${budget||"—"}</strong><small>Reserved allowance, not Meta account balance</small></div></div>
   <nav className="studio-steps" aria-label="Studio workflow">{steps.map((label,i)=><button key={label} onClick={()=>{setStep(i);if(i===5)loadBoard().catch(()=>{})}} className={step===i?"studio-step selected":"studio-step"} aria-current={step===i?"step":undefined}><span>{i+1}</span><b>{label}</b></button>)}</nav>
   {error&&<div className="alert error" role="alert">{error}<button onClick={()=>setError("")}>×</button></div>}
   {notice&&<div className="alert" role="status">{notice}<button onClick={()=>setNotice("")}>×</button></div>}
   {step===0&&<div className="studio-layout"><div className="panel"><span className="eyebrow">01 · BUSINESS CONTEXT</span><h2>Tell us about your business</h2><label>Business name<input value={businessName} onChange={e=>setBusinessName(e.target.value)}/></label><label>Website (optional, not automatically fetched)<input type="url" value={website} onChange={e=>setWebsite(e.target.value)}/></label><label>Business description<textarea rows={5} value={description} onChange={e=>setDescription(e.target.value)} maxLength={4000}/></label><label>Main objective<textarea rows={2} value={goal} onChange={e=>setGoal(e.target.value)}/></label><div className="studio-columns"><label>Campaign language<select value={language} onChange={e=>setLanguage(e.target.value as typeof language)}><option value="en">English</option><option value="bn">বাংলা</option><option value="hi">हिन्दी</option></select></label><div><label>Social platforms</label>{["instagram","facebook","whatsapp"].map(p=><label className="studio-choice" key={p}><input type="checkbox" checked={platforms.includes(p)} onChange={e=>setPlatforms(x=>e.target.checked?[...x,p]:x.filter(v=>v!==p))}/>{p}</label>)}</div></div><button className="primary" disabled={busy||!platforms.length||description.length<25} onClick={generateCampaign}>{busy?"Preparing…":"Generate business audit & campaign →"}</button><p className="muted">Your owner workspace uses real Meta inference. Sample data is used only when you explicitly select it or enter a guest workspace.</p></div><div className="panel"><span className="eyebrow">PRODUCT PHOTOS</span><h2>Measure visual readiness</h2><p className="muted">Resolution, brightness, contrast, texture and colors are measured from the actual pixels. Meta visual ratings are separate.</p><label>Upload one product photo<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>setFile(e.target.files?.[0]||null)}/></label><button className="secondary wide" disabled={!file||busy} onClick={scorePhoto}>Score image</button>{images.map(img=><article className="studio-photo" key={img.id}><div><b>{img.filename}</b><Flag value={img.result.provenance}/></div><div className="studio-score"><strong>{img.result.local.technical_readiness}<small>/100</small></strong><span>Technical readiness (heuristic)</span></div><p>Brightness {img.result.local.brightness} · Contrast {img.result.local.contrast} · {img.result.local.width} × {img.result.local.height}</p><div className="studio-palette">{img.result.local.dominant_colors.map((color,i)=><span key={i} style={{background:color}} title={color}/>)}</div>{img.result.model&&<p>AI assessment: {img.result.model.overall}/100</p>}</article>)}</div></div>}
   {step===1&&<div className="panel"><span className="eyebrow">02 · EVIDENCE & POSITIONING</span><h2>Business opportunity audit</h2>{campaign?<><Flag value={campaign.provenance}/><div className="studio-columns"><article className="studio-inset"><small>OFFER SUMMARY</small><p>{campaign.audit.analysis.offer_summary}</p></article><article className="studio-inset"><small>LIKELY AUDIENCE (HYPOTHESIS)</small><p>{campaign.audit.analysis.audience_guess}</p></article></div><h3>Gaps requiring review</h3>{campaign.audit.analysis.gaps.map((gap,i)=><article className="finding" key={i}><p>{gap.finding}</p><small>{gap.assumption?"Assumption · not independently established":`Source reference: ${gap.evidence_id}`}</small></article>)}<h3>Positioning directions</h3><div className="studio-columns">{campaign.audit.analysis.positioning_angles.map((p,i)=><article className="studio-inset" key={i}><small>ANGLE {i+1}</small><p>{p}</p></article>)}</div><details><summary>View evidence provenance</summary><pre>{JSON.stringify(campaign.audit.evidence,null,2)}</pre></details><button className="primary" onClick={()=>setStep(2)}>Review seven-day plan →</button></>:<p className="muted">Generate a business audit from the Brief step first.</p>}</div>}
   {step===2&&<div className="panel"><div className="studio-heading"><div><span className="eyebrow">03 · CAMPAIGN CALENDAR</span><h2>Seven days of content</h2></div>{campaign&&<Flag value={campaign.provenance}/>}</div>{campaign?<><div className="studio-daygrid">{campaign.items.map(item=><article className="studio-day" key={item.id}><div className="studio-daytop"><span>DAY {item.day} · {item.platform}</span><Flag value={item.provenance}/></div><small>{item.post_type}</small><p>{item.caption}</p><div className="studio-tags">{item.hashtags.map(tag=><span key={tag}>{tag}</span>)}</div><p className="muted"><b>CTA:</b> {item.cta}</p>{item.unsupported_claims?.length>0&&<p className="studio-warning">Review unsupported claims: {item.unsupported_claims.join(", ")}</p>}<details><summary>Edit caption and creative brief</summary><label>Caption<textarea key={item.id+"caption"} defaultValue={item.caption} onBlur={e=>{if(e.target.value!==item.caption)updateItem(item,"caption",e.target.value)}}/></label><label>Creative brief<textarea key={item.id+"creative"} defaultValue={item.creative_brief} onBlur={e=>{if(e.target.value!==item.creative_brief)updateItem(item,"creative_brief",e.target.value)}}/></label></details><button className="secondary wide" onClick={()=>{setItemId(item.id);setVariants([]);setStep(3)}}>Create visuals →</button></article>)}</div><button className="primary" onClick={()=>setStep(4)}>Build a landing page →</button></>:<p className="muted">No campaign generated yet.</p>}</div>}
   {step===3&&<div className="panel"><span className="eyebrow">04 · CREATIVE EXPLORATION</span><h2>Compare campaign visuals</h2>{campaign?<><label>Choose campaign day<select value={itemId} onChange={e=>{setItemId(e.target.value);setVariants([]);setSelectedVariant(null)}}>{campaign.items.map(i=><option key={i.id} value={i.id}>Day {i.day} · {i.platform}</option>)}</select></label><div className="studio-columns"><label>Brand mood<input value={brandMood} onChange={e=>setBrandMood(e.target.value)}/></label><label>Number of variants<select value={requestedVariants} onChange={e=>setRequestedVariants(Number(e.target.value))}><option value={1}>1</option><option value={2}>2</option><option value={3}>3</option></select></label></div><p className="muted">Live Meta image generation may consume promotional credits. Server-side opt-in, budget reservation and workspace quotas must be enabled.</p><button className="primary" disabled={busy} onClick={createVariants}>{busy?"Generating…":"Generate & compare creatives"}</button><div className="studio-creativegrid">{variants.map(v=><article className={v.selected?"studio-creative chosen":"studio-creative"} key={v.id}>{variantImages[v.id]?<img src={variantImages[v.id]} alt="Generated or sample visual for campaign item"/>:<div className="studio-noimage">Preview unavailable</div>}<div className="studio-creativebody"><div className="studio-daytop"><Flag value={v.provenance}/>{v.recommended&&<span className="studio-badge">Recommended for review</span>}</div><p>Technical readiness: <b>{v.scores.local.technical_readiness}/100</b></p>{v.scores.brief_match&&<p>Brief match: {v.scores.brief_match.brief_match}/100</p>}<button className="secondary wide" disabled={busy} onClick={()=>pickVariant(v)}>{v.selected?"Selected ✓":"Select this concept"}</button></div></article>)}</div><button className="secondary" onClick={()=>setStep(4)}>Continue to landing page →</button></>:<p className="muted">Create a campaign first.</p>}</div>}
   {step===4&&<div className="studio-layout"><div className="panel"><span className="eyebrow">05 · CONVERSION LANDING PAGE</span><h2>Build your conversion destination</h2><label>Template<select value={pageTheme} onChange={e=>setPageTheme(e.target.value)}><option value="modern">Modern</option><option value="warm">Warm</option><option value="bold">Bold</option></select></label><label>Business WhatsApp (optional, international format)<input value={whatsapp} onChange={e=>setWhatsapp(e.target.value)} placeholder="+919876543210"/></label><button className="primary wide" disabled={busy||!campaign} onClick={createLanding}>{busy?"Generating…":"Generate page draft"}</button>{page&&<><div className="studio-inset"><Flag value={page.provenance}/><p><b>{page.spec.headline}</b></p><small>{page.published?"Published":"Unpublished draft"} · {page.leads_count} leads</small></div>{(["headline","subheadline","offer"] as const).map(field=><label key={field}>{field.replaceAll("_"," ")}<textarea key={page.id+field+String(page.spec[field])} defaultValue={String(page.spec[field])} rows={2} onBlur={e=>{if(e.target.value!==String(page.spec[field]))saveLandingText(field,e.target.value)}}/></label>)}<div className="studio-buttonrow"><button className="secondary" onClick={()=>publish(!page.published)} disabled={busy}>{page.published?"Unpublish":"Publish (requires approval)"}</button><button className="secondary" onClick={()=>download(`/api/v1/landing/${page.id}/export?workspace_id=${encodeURIComponent(workspace)}`,"sentinelx-landing.html")}>Download HTML</button></div>{page.published&&<p className="muted">Public path: <a href={page.url} target="_blank" rel="noreferrer">{page.url}</a></p>}<button className="secondary" onClick={loadLeads}>View inquiries</button>{leads.map(l=><article className="finding" key={l.id}><b>{l.name}</b><p>{l.phone}</p><p>{l.message}</p></article>)}</>}</div><div className="panel"><span className="eyebrow">SAFE LIVE PREVIEW</span><h3>Responsive, script-free HTML</h3>{preview?<iframe title="Landing preview" className="studio-preview" srcDoc={preview} sandbox="" referrerPolicy="no-referrer"/>:<div className="studio-empty">Generate a landing page to see the rendered preview.</div>}<p className="muted">Preview is sandboxed. Only explicitly approved pages can be made public.</p><button className="secondary wide" onClick={()=>{setStep(5);loadBoard().catch(()=>{})}}>Review approvals →</button></div></div>}
   {step===5&&<div className="panel"><div className="studio-heading"><div><span className="eyebrow">06 · HUMAN GOVERNANCE</span><h2>Approval board & delivery pack</h2><p className="muted">Only approved deliverables enter the ZIP; all decisions are recorded with reviewer, time and optional notes.</p></div><button className="secondary" onClick={()=>loadBoard().catch(e=>setError(String(e)))}>Refresh board</button></div>{campaign?<><label>Optional review note<input value={reviewNote} maxLength={500} onChange={e=>setReviewNote(e.target.value)} placeholder="Why is this approved or rejected?"/></label><div className="studio-kanban">{(["proposed","approved","rejected"] as const).map(state=><div key={state} className="studio-column"><h3>{state[0].toUpperCase()+state.slice(1)} · {board.filter(a=>a.state===state).length}</h3>{board.filter(a=>a.state===state).map(a=><article className="studio-review" key={a.id}><span className="studio-badge">{a.target_kind.replaceAll("_"," ")}</span><p>{a.target_id.slice(0,10)}…</p><small>{a.events.length} audited decisions</small><div className="studio-buttonrow">{state==="proposed"?<><button onClick={()=>decide(a,"approved")} disabled={busy}>Approve</button><button onClick={()=>decide(a,"rejected")} disabled={busy}>Reject</button></>:<button onClick={()=>decide(a,"reopen")} disabled={busy}>Reopen</button>}</div></article>)}</div>)}</div><button className="primary" onClick={()=>download(`/api/v1/campaigns/${campaign.id}/export?workspace_id=${encodeURIComponent(workspace)}&format=zip`,"sentinelx-approved-pack.zip")}>↓ Download approved campaign pack</button><p className="muted">Export does not auto-publish to Instagram, Facebook or WhatsApp.</p></>:<p className="muted">Create a campaign first.</p>}</div>}
   <footer className="studio-footer"><span>All AI judgments require human verification · No external publishing</span><div><button className="secondary" disabled={step===0} onClick={()=>setStep(x=>Math.max(0,x-1))}>← Back</button><button className="secondary" disabled={step===5} onClick={()=>{setStep(x=>Math.min(5,x+1));if(step===4)loadBoard().catch(()=>{})}}>Next →</button></div></footer>
 </section>;
}
