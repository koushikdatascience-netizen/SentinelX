"use client";
import {useEffect,useRef,useState} from "react";
import type {BusinessProfile} from "./BusinessProfile";
import type {WorkbenchTool} from "./BusinessWorkbench";
import {EmptyState,Modal,ProductIcon,SourceBadge} from "./ProductUI";
import PromptVoiceInput from "./PromptVoiceInput";
export type StudioView="dashboard"|"brief"|"photos"|"audit"|"campaign"|"creatives"|"landing"|"approvals";

const BASE=process.env.NEXT_PUBLIC_API_URL ?? "";
type Provenance="live_meta"|"sample"|"user_supplied";
type Img={id:string;filename:string;previewUrl?:string;result:{local:{width:number;height:number;brightness:number;contrast:number;edge_variance:number;technical_readiness:number;dominant_colors:string[]};model?:{overall:number;issues:string[];fixes:string[]}|null;provenance:Provenance}};
type Item={id:string;day:number;platform:string;post_type:string;caption:string;hashtags:string[];cta:string;creative_brief:string;image_prompt?:string;video_script?:string|null;state:string;provenance:Provenance;unsupported_claims:string[]};
type Campaign={id:string;duration_days?:number;tone?:string;requirements?:string;business_description:string;goal:string;language:string;provenance:Provenance;audit:{analysis:{offer_summary:string;audience_guess:string;gaps:{finding:string;assumption:boolean;evidence_id:string|null}[];positioning_angles:string[]};evidence:{id:string;text?:string;url?:string;type:string}[]};items:Item[]};
type Variant={id:string;selected:boolean;recommended:boolean;provenance:Provenance;mime:string;prompt:string;scores:{local:{technical_readiness:number};brief_match?:{brief_match:number}|null;final_score:number|null}};
type Page={id:string;campaign_id:string;slug:string;url:string;published:boolean;leads_count:number;provenance:Provenance;spec:{business_name:string;headline:string;subheadline:string;offer:string;cta_label:string;theme:string;accent_color:string;hero_image_variant_id:string|null;[key:string]:unknown}};
type Approval={id:string;target_kind:string;target_id:string;title:string;description:string;state:string;events:{decision:string;note:string;reviewer_id:string;at:string}[]};
type Lead={id:string;name:string;phone:string;message:string;created_at:string};
type Runtime={mode:"sample"|"live"|"unavailable";is_guest:boolean;live_enabled:boolean;message:string};
type SavedCampaign={id:string;goal:string;provenance:Provenance};
const PLATFORM_OPTIONS=[{id:"instagram",label:"Instagram"},{id:"facebook",label:"Facebook"},{id:"whatsapp",label:"WhatsApp"},{id:"linkedin",label:"LinkedIn"},{id:"x",label:"X (Twitter)"},{id:"google_business_profile",label:"Google Business Profile"},{id:"youtube",label:"YouTube"},{id:"blogger",label:"Blogger"}];
const platformName=(value:string)=>PLATFORM_OPTIONS.find(option=>option.id===value)?.label||value;
const GOAL_OPTIONS=["Generate qualified inquiries","Increase brand awareness","Promote a product or service","Drive website visits","Encourage repeat purchases","Grow an engaged audience"];
const demoDescription="";
export default function BusinessStudio({token,workspace,view,onNavigate,onReports,onSettings,onTool}:{token:string;workspace:string;view:StudioView;onTool:(tool:WorkbenchTool|StudioView)=>void;onNavigate:(view:StudioView)=>void;onReports:()=>void;onSettings:()=>void}){
 const [website,setWebsite]=useState("");
 const [description,setDescription]=useState(demoDescription);
 const [businessName,setBusinessName]=useState("");
 const [goal,setGoal]=useState(GOAL_OPTIONS[0]);
 const [requirements,setRequirements]=useState("");const [durationDays,setDurationDays]=useState<7|10|30>(7);const [tone,setTone]=useState("professional");
 const [voiceBusy,setVoiceBusy]=useState(false);const [profileReady,setProfileReady]=useState(false);
 const campaignRequest=useRef<{signature:string;id:string}|null>(null);
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
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 const [notice,setNotice]=useState("");
 const [brandMood,setBrandMood]=useState("warm, contemporary and handcrafted");
 const [requestedVariants,setRequestedVariants]=useState(1);
 const [pageTheme,setPageTheme]=useState("warm");
 const [whatsapp,setWhatsapp]=useState("");
 const [activity,setActivity]=useState("Saving changes…");
 const [editor,setEditor]=useState<Item|null>(null);
 const [editFields,setEditFields]=useState({caption:"",hashtags:"",cta:"",creative_brief:"",image_prompt:"",video_script:""});
 const [editLanding,setEditLanding]=useState(false);
 const [landingFields,setLandingFields]=useState({headline:"",subheadline:"",offer:""});
 const [showInquiries,setShowInquiries]=useState(false);
 const [expandedPreview,setExpandedPreview]=useState(false);
 const [reviewItem,setReviewItem]=useState<Approval|null>(null);
 const [reviewFilter,setReviewFilter]=useState("proposed");
 const [platformFilter,setPlatformFilter]=useState("all");
 const [landingPages,setLandingPages]=useState<Page[]>([]);
 const photoUrls=useRef<string[]>([]);
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
   setBusy(true);setError("");setNotice("");setActivity("Saving changes…");
   try{await fn()}catch(e){setError(e instanceof Error?e.message:"Something went wrong")}
   finally{setBusy(false)}
 }
 useEffect(()=>{setImages([]);setCampaign(null);setVariants([]);setPage(null);setBoard([]);setSelectedVariant(null);setLandingPages([]);setEditor(null);setReviewItem(null);setError("");setNotice("");photoUrls.current.forEach(URL.revokeObjectURL);photoUrls.current=[];},[workspace]);
 useEffect(()=>()=>photoUrls.current.forEach(URL.revokeObjectURL),[]);
 useEffect(()=>{let active=true;setProfileReady(false);if(workspace)api<BusinessProfile|null>(`/api/v1/workspaces/${workspace}/business-profile`).then(profile=>{if(active&&profile){setBusinessName(profile.details.name);setWebsite(profile.details.website);setDescription(profile.details.description);setWhatsapp(profile.details.phone);setProfileReady(true)}}).catch(()=>{});return()=>{active=false}},[token,workspace]);
 useEffect(()=>{if(campaign)loadBoard().catch(e=>setError(String(e)))},[campaign,page,view]);
 useEffect(()=>{
   let active=true;
   api<Runtime>("/api/v1/campaigns/runtime").then(r=>{if(active)setRuntime(r)}).catch(e=>{if(active)setError(String(e))});
   if(workspace)api<SavedCampaign[]>(`/api/v1/campaigns?workspace_id=${encodeURIComponent(workspace)}`).then(async rows=>{
     if(!active)return;setSavedCampaigns(rows);
     if(rows.length)await openCampaign(rows[0].id,false);
   }).catch(e=>{if(active)setError(String(e))});
   return()=>{active=false};
 },[token,workspace]);
 useEffect(()=>()=>{Object.values(variantImages).forEach(x=>URL.revokeObjectURL(x))},[variantImages]);
 async function scorePhoto(){
   if(!file)return;
   await action(async()=>{
     setActivity("Reviewing your photo…");
     const form=new FormData();form.append("workspace_id",workspace);form.append("business_context",description.slice(0,1500));form.append("file",file);
     form.append("generation_mode",generationMode);
     const response=await fetch(BASE+"/api/v1/images/score",{method:"POST",headers:{Authorization:"Bearer "+token},body:form});
     const result=await response.json();if(!response.ok)throw new Error(typeof result.detail==="string"?result.detail:"Image score failed");
     const previewUrl=URL.createObjectURL(file);photoUrls.current.push(previewUrl);
     setImages(previous=>[...previous,{...result,previewUrl} as Img]);setFile(null);
     setNotice("Image measured and saved. AI evaluation only appears when a real model runs.");
   });
 }
 async function generateCampaign(){
   await action(async()=>{
     setActivity("Creating your campaign…");
     if(generationMode==="live"&&(!runtime||runtime.mode==="unavailable"))throw new Error(runtime?.message||"Checking generation service. Try again shortly.");
     const payload={workspace_id:workspace,goal,language,platforms,image_ids:images.map(x=>x.id),generation_mode:generationMode,duration_days:durationDays,tone,requirements};
     const signature=JSON.stringify(payload);if(campaignRequest.current?.signature!==signature)campaignRequest.current={signature,id:crypto.randomUUID()};
     const c=await api<Campaign>("/api/v1/campaigns","POST",{
       ...payload,request_id:campaignRequest.current.id
     });
     setSavedCampaigns(old=>[{id:c.id,goal:c.goal,provenance:c.provenance},...old.filter(item=>item.id!==c.id)]);
     setCampaign(c);setItemId(c.items[0]?.id||"");onNavigate("campaign");
     setNotice(c.provenance==="live_meta"?"Live Meta audit generated; review every claim.":"Clearly labeled sample campaign generated without model charges.");
   });
 }
 async function openCampaign(id:string,fillBrief=true){
   const c=await api<Campaign>(`/api/v1/campaigns/${id}?workspace_id=${encodeURIComponent(workspace)}`);
   setCampaign(c);setSampleMode(c.provenance==="sample");setItemId(c.items[0]?.id||"");if(fillBrief){setGoal(c.goal);setRequirements(c.requirements||"");setTone(c.tone||"professional");setDurationDays((c.duration_days===10||c.duration_days===30)?c.duration_days:7);}setDescription(c.business_description);setVariants([]);setPage(null);setPreview("");setBoard([]);
   const pages=await api<Page[]>(`/api/v1/landing?workspace_id=${encodeURIComponent(workspace)}`);
   setLandingPages(pages.filter(p=>p.campaign_id===c.id));
   const existing=pages.find(p=>p.campaign_id===c.id);
   if(existing){setPage(existing);setBusinessName(existing.spec.business_name);await loadPreview(existing.id)}
   const first=c.items[0];
   if(first){const vs=await api<Variant[]>(`/api/v1/campaigns/${c.id}/items/${first.id}/creatives?workspace_id=${encodeURIComponent(workspace)}`);
     setVariants(vs);setSelectedVariant(vs.find(v=>v.selected)?.id||null);await fetchVariantImages(c.id,first.id,vs)}
 }
 async function openCreativeItem(id:string){
   if(!campaign)return;
   setItemId(id);
   const vs=await api<Variant[]>(`/api/v1/campaigns/${campaign.id}/items/${id}/creatives?workspace_id=${encodeURIComponent(workspace)}`);
   setVariants(vs);setSelectedVariant(vs.find(v=>v.selected)?.id||null);
   await fetchVariantImages(campaign.id,id,vs);
 }
 async function createVariants(){
   if(!campaign||!itemId)return;
   await action(async()=>{
     setActivity("Creating and reviewing your visual…");
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
     setActivity("Writing your landing page…");
     const result=await api<Page>("/api/v1/landing/generate","POST",{workspace_id:workspace,
       campaign_id:campaign.id,business_name:businessName,theme:pageTheme,
       whatsapp_number:whatsapp||null,hero_image_variant_id:selectedVariant||null,generation_mode:generationMode});
     setPage(result);setLandingPages(previous=>[result,...previous]);await loadPreview(result.id);
     setNotice("Landing page created as an unpublished draft. Approval required.");
   });
 }
 async function loadPreview(pid=page?.id){
   if(!pid)return;
   const res=await fetch(BASE+`/api/v1/landing/${pid}/preview?workspace_id=${encodeURIComponent(workspace)}`,{
     headers:{Authorization:"Bearer "+token}});
   if(!res.ok)throw Error("Landing preview failed");setPreview(await res.text());
 }
 async function publish(value:boolean){
   if(!page)return;
   await action(async()=>{
     const updated=await api<Page>(`/api/v1/landing/${page.id}?workspace_id=${encodeURIComponent(workspace)}`,"PATCH",{published:value});
     setPage(updated);setLandingPages(old=>old.map(p=>p.id===updated.id?updated:p));setNotice(value?"Page published on this application host.":"Page unpublished.");
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
     await loadBoard();setReviewItem(null);
     setNotice(`Decision ${decision} recorded; no external publishing performed.`);
   });
 }
 async function download(path:string,name:string){
   await action(async()=>{
     const res=await fetch(BASE+path,{headers:{Authorization:"Bearer "+token}});
     if(!res.ok)throw Error("Export unavailable");
     const url=URL.createObjectURL(await res.blob());
     const link=document.createElement("a");link.href=url;link.download=name;document.body.appendChild(link);
     link.click();link.remove();URL.revokeObjectURL(url);
     setNotice(name+" downloaded.");
   });
 }

 async function savePost(){
   if(!campaign||!editor)return;
   await action(async()=>{
     const changed=await api<Item>(`/api/v1/campaigns/${campaign.id}/items/${editor.id}?workspace_id=${encodeURIComponent(workspace)}`,"PATCH",{
       ...editFields,hashtags:editFields.hashtags.split(/[\s,]+/u).map(tag=>tag.trim()).filter(Boolean),video_script:editFields.video_script.trim()||null
     });
     setCampaign(old=>old?{...old,items:old.items.map(item=>item.id===editor.id?{...item,...changed}:item)}:old);
     setEditor(null);setNotice("Post updated. Your edits are saved.");
   });
 }
 async function savePage(){
   if(!page)return;
   await action(async()=>{
     const updated=await api<Page>(`/api/v1/landing/${page.id}?workspace_id=${encodeURIComponent(workspace)}`,"PATCH",{spec:{...page.spec,...landingFields}});
     setPage(updated);setLandingPages(old=>old.map(p=>p.id===updated.id?updated:p));await loadPreview(updated.id);setEditLanding(false);setNotice("Page changes saved.");
   });
 }
 function editPost(item:Item){setEditFields({caption:item.caption,hashtags:item.hashtags.join(" "),cta:item.cta,creative_brief:item.creative_brief,image_prompt:item.image_prompt||item.creative_brief,video_script:item.video_script||""});setEditor(item)}
 async function copy(text:string){try{await navigator.clipboard.writeText(text);setNotice("Copied to clipboard.")}catch{setError("Clipboard access is unavailable in this browser.")}}
 const titles:Record<StudioView,[string,string]>={
   dashboard:["Your business workspace","Understand, research, create, approve and verify business improvements."],
   brief:["Create a campaign","Choose your goal and tell us what this campaign needs. Your saved business profile supplies the context."],
   photos:["Photo review","Understand what works in your product photos and what to improve."],
   audit:["Business strategy","A clear view of your offer, audience and opportunities."],
   campaign:["Campaign calendar","Review and edit every caption, hashtag, call to action and creative direction in one sheet."],
   creatives:["Creative studio","Generate visual concepts and choose the one that fits your campaign."],
   landing:["Landing pages","Turn your campaign into a page customers can act on."],
   approvals:["Review & export","Review your deliverables and download an approved campaign pack."]
 };
 const tools:{title:string;description:string;icon:string;action:()=>void}[]=[
   {title:"Create campaign",description:"Strategy, captions, visual briefs and a content calendar.",icon:"campaign",action:()=>onTool("brief")},
   {title:"Competitor research",description:"Source-linked businesses by industry and location.",icon:"globe",action:()=>onTool("competitors")},
   {title:"Post generator",description:"A post, image prompt and reel or shorts scene plan.",icon:"spark",action:()=>onTool("post")},
   {title:"SEO keywords & hashtags",description:"Relevant search phrases and evidence-led hashtag ideas.",icon:"report",action:()=>onTool("keywords")},
   {title:"Image generator",description:"Original business visuals from your prompt and context.",icon:"image",action:()=>onTool("image")},
   {title:"Image editor",description:"Crop, resize, rotate and convert your image locally.",icon:"edit",action:()=>onTool("image_editor")},
   {title:"Document parser",description:"Extract large PDFs in batches and export text or JSON.",icon:"report",action:()=>onTool("documents")},
   {title:"Review a photo",description:"Practical feedback on your product images.",icon:"image",action:()=>onTool("photos")},
   {title:"Landing pages",description:"Build and review a page for your campaign.",icon:"landing",action:()=>onTool("landing")},
   {title:"Review & export",description:"Approve content and export your delivery pack.",icon:"review",action:()=>onTool("approvals")},
 ];
 const selectedVisual=variants.find(v=>v.selected)||variants[0];
 const heroUrl=selectedVisual?variantImages[selectedVisual.id]:null;
 const pending=board.filter(a=>a.state==="proposed").length;
 const approved=board.filter(a=>a.state==="approved").length;
 const landingReview=page?board.find(a=>a.target_kind==="landing"&&a.target_id===page.id):undefined;
 const landingApproved=landingReview?.state==="approved";
 const needCampaign=<EmptyState title="Start with a campaign" action={<button className="primary" onClick={()=>onNavigate("brief")}><ProductIcon name="plus"/>Create campaign</button>}>Create a campaign or open saved work from the dashboard to use this tool.</EmptyState>;
 if(!workspace)return <EmptyState icon="dashboard" title="Let’s set up your workspace" action={<button className="primary" onClick={onSettings}>Create a workspace<ProductIcon name="arrow"/></button>}>Give your business a workspace to keep its campaigns, photos and pages together.</EmptyState>;
 return <section className="dashboard-ui">
   {view!=="dashboard"&&<button className="breadcrumb-back" onClick={()=>onNavigate("dashboard")}><ProductIcon name="back" size={16}/>Dashboard</button>}
   <div className="product-page-head"><div><div className="page-kicker">{view==="dashboard"?"WORKSPACE":"YOUR TOOLS"}</div><h1>{titles[view][0]}</h1><p>{titles[view][1]}</p></div>
     <div className="page-head-actions">{view==="dashboard"?<span className={`runtime-pill ${runtime?.mode==="live"?"runtime-live":""}`}><span/>{runtime?.mode==="live"?"Live AI enabled":runtime?.mode==="sample"?"Sample workspace":runtime?.mode==="unavailable"?"AI unavailable":"Checking AI service"}</span>:savedCampaigns.length>0&&view!=="brief"&&view!=="photos"?<label className="campaign-picker">Campaign<select aria-label="Saved campaigns" value={campaign?.id||""} disabled={busy} onChange={e=>action(()=>openCampaign(e.target.value))}>{savedCampaigns.map(c=><option key={c.id} value={c.id}>{c.goal}</option>)}</select></label>:null}</div>
   </div>
   {error&&<div className="product-notice notice-error" role="alert"><ProductIcon name="close"/><span>{error}</span><button aria-label="Dismiss error" onClick={()=>setError("")}><ProductIcon name="close" size={16}/></button></div>}
   {notice&&<div className="product-notice" role="status"><ProductIcon name="check"/><span>{notice}</span><button aria-label="Dismiss notification" onClick={()=>setNotice("")}><ProductIcon name="close" size={16}/></button></div>}
   {runtime?.mode==="unavailable"&&<div className="product-notice notice-warning">Live AI is unavailable in this workspace. You can still review saved work or explicitly choose sample content when creating a campaign.</div>}
   {view==="dashboard"&&<>
     <div className="section-heading"><h2>What would you like to do?</h2><span>Everything you need, in one place</span></div>
     <div className="tool-grid">{tools.map((tool,i)=><button className="tool-card" key={tool.title} onClick={tool.action}><span className={`tool-icon tool-tone-${i%4}`}><ProductIcon name={tool.icon} size={23}/></span><span className="tool-card-copy"><strong>{tool.title}</strong><small>{tool.description}</small></span><ProductIcon name="arrow" size={17}/></button>)}</div>
     <div className="dashboard-work-grid"><section className="product-card recent-work"><div className="section-heading"><h2>Continue your work</h2>{campaign&&<SourceBadge value={campaign.provenance}/>}</div>{campaign?<><div className="campaign-spotlight"><div><span className="small-label">LATEST CAMPAIGN</span><h3>{campaign.goal}</h3><p>{campaign.audit.analysis.offer_summary}</p><div className="spotlight-meta"><span>{campaign.items.length} posts</span><span>{[...new Set(campaign.items.map(i=>i.platform))].join(" · ")}</span><span>{campaign.language.toUpperCase()}</span></div><button className="primary" onClick={()=>onNavigate("campaign")}>Open campaign<ProductIcon name="arrow" size={17}/></button></div>{heroUrl?<button className="spotlight-visual" aria-label="Open saved creative" onClick={()=>onNavigate("creatives")}><img src={heroUrl} alt="Your saved campaign creative"/><span>View creative<ProductIcon name="arrow" size={15}/></span></button>:<button className="spotlight-no-visual" onClick={()=>onNavigate("creatives")}><ProductIcon name="image" size={34}/><span>Create your first visual</span></button>}</div>{savedCampaigns.length>1&&<div className="recent-campaign-list">{savedCampaigns.slice(1,4).map(c=><button key={c.id} onClick={()=>action(async()=>{await openCampaign(c.id);onNavigate("campaign")})}><ProductIcon name="campaign"/><span>{c.goal}</span><ProductIcon name="arrow" size={16}/></button>)}</div>}</>:<EmptyState title="Your next campaign starts here" action={<button className="primary" onClick={()=>onNavigate("brief")}>Create your first campaign</button>}>Add a short business brief. Your saved strategy, posts and designs will appear here.</EmptyState>}</section>
     <section className="product-card review-summary"><div className="section-heading"><h2>Ready for review</h2><span className="count-pill">{pending}</span></div>{pending?<><p className="section-description">Take a look before anything is published.</p>{board.filter(a=>a.state==="proposed").slice(0,3).map(a=><button className="review-summary-row" key={a.id} onClick={()=>{onNavigate("approvals");setReviewItem(a)}}><span className="review-type-icon"><ProductIcon name={a.target_kind==="landing"?"landing":a.target_kind==="creative"?"image":"campaign"} size={18}/></span><span><strong>{a.title}</strong><small>{a.target_kind.replaceAll("_"," ")}</small></span><ProductIcon name="arrow" size={15}/></button>)}<button className="text-link" onClick={()=>onNavigate("approvals")}>Review all deliverables<ProductIcon name="arrow" size={16}/></button></>:<EmptyState icon="review" title="All caught up">New posts, selected visuals and pages will appear here for your review.</EmptyState>}</section></div>
   </>}
   {view==="brief"&&<div className="creation-layout"><section className="product-card form-card"><div className="campaign-business-context"><span className="small-label">USING YOUR SAVED BUSINESS PROFILE</span><h2>{profileReady?businessName:"Your business context"}</h2><p className="field-help">{profileReady?"Business details are included automatically. Update them in Business & research.":"Save your business profile in Business & research before generating."}</p></div><form onSubmit={e=>{e.preventDefault();generateCampaign()}}><div className="field-grid"><label>Campaign goal<select value={GOAL_OPTIONS.includes(goal)?goal:"custom"} onChange={e=>setGoal(e.target.value==="custom"?"":e.target.value)}>{GOAL_OPTIONS.map(value=><option key={value} value={value}>{value}</option>)}<option value="custom">Custom goal…</option></select></label><label>Campaign duration<select value={durationDays} onChange={e=>{const days=Number(e.target.value) as 7|10|30;setDurationDays(days);if(platforms.length>Math.min(8,days)){setPlatforms(platforms.slice(0,Math.min(8,days)));setNotice("Platform selection adjusted to fit one post per day.")}}}><option value={7}>1 week · 7 days</option><option value={10}>10 days</option><option value={30}>1 month · 30 days</option></select></label></div>{!GOAL_OPTIONS.includes(goal)&&<label>Custom goal<textarea required rows={2} minLength={10} maxLength={600} value={goal} onChange={e=>setGoal(e.target.value)} placeholder="Describe what the campaign should achieve."/></label>}<div className="field-grid"><label>Campaign tone<select value={tone} onChange={e=>setTone(e.target.value)}>{["professional","friendly","informative","bold","playful","premium"].map(value=><option key={value} value={value}>{value[0].toUpperCase()+value.slice(1)}</option>)}</select></label><label>Content language<select value={language} onChange={e=>setLanguage(e.target.value as typeof language)}><option value="en">English</option><option value="bn">বাংলা</option><option value="hi">हिन्दी</option></select></label></div><fieldset className="platform-options"><legend>Where will you share it?</legend>{PLATFORM_OPTIONS.map(({id,label})=><label key={id}><input type="checkbox" checked={platforms.includes(id)} disabled={!platforms.includes(id)&&platforms.length>=Math.min(8,durationDays)} onChange={e=>setPlatforms(old=>e.target.checked?[...old,id]:old.filter(p=>p!==id))}/>{label}</label>)}<small className="platform-selection-count">{platforms.length} of {Math.min(8,durationDays)} platforms selected · one content row per day</small></fieldset><label htmlFor="campaign-requirements">Campaign requirements<textarea id="campaign-requirements" required rows={5} minLength={10} maxLength={4000} value={requirements} onChange={e=>setRequirements(e.target.value)} placeholder="Tell us what to focus on: products, audience, message, confirmed offers, preferred formats, dates or anything to avoid."/></label><div className="campaign-composer-toolbar"><span className="field-help">{requirements.length}/4000</span><PromptVoiceInput compact token={token} workspace={workspace} disabled={busy} available={Boolean(runtime?.live_enabled&&!sampleMode)} onActivityChange={setVoiceBusy} onTranscript={text=>setRequirements(current=>[current.trimEnd(),text].filter(Boolean).join(" ").slice(0,4000))}/><button className="primary" disabled={busy||voiceBusy||!profileReady||!platforms.length||requirements.trim().length<10}><ProductIcon name="arrow" size={17}/>{generationMode==="sample"?"Create sample campaign":"Generate campaign"}</button></div><p className="field-help">Click the mic to record; allow microphone access when your browser asks. Stopping sends audio to Meta and inserts editable text here. It does not submit your campaign.</p>{runtime&&!runtime.is_guest&&<details className="subtle-details"><summary>Generation options</summary><label className="checkbox-label"><input type="checkbox" checked={sampleMode} onChange={e=>setSampleMode(e.target.checked)}/>Use sample data (no credits)</label><p>Samples are clearly labeled and don’t call an AI model. Voice transcription requires live mode.</p></details>}</form></section><aside className="creation-guide product-card"><span className="guide-icon"><ProductIcon name="spark" size={27}/></span><h3>{durationDays} days. One campaign brief.</h3><p>Your saved business context, goal and requirements guide the content.</p><ul><li><ProductIcon name="check" size={16}/>{durationDays} daily content rows across your selected platforms</li><li><ProductIcon name="check" size={16}/>Captions, hashtags and calls to action</li><li><ProductIcon name="check" size={16}/>Image guidance and generation prompts</li><li><ProductIcon name="check" size={16}/>Video scripts for Reel, Short and video formats</li></ul><div className="guide-note">{generationMode==="sample"?"Sample mode: no model calls.":`Up to ${Math.ceil(durationDays/7)} budgeted model request(s), generated in batches of up to 7 days. Voice uses one separate request per recording. No automatic paid retries.`}</div><small>Review every claim and draft before use. Nothing is automatically published.</small></aside></div>}

   {view==="photos"&&<div className="photo-review-layout"><section className="product-card form-card"><h2>Add a product photo</h2><p className="section-description">Choose a clear photo of the product or scene you want to use.</p><label className="photo-dropzone"><ProductIcon name="upload" size={32}/><strong>{file?file.name:"Choose a product photo"}</strong><span>PNG, JPEG or WebP · Up to 5 MB</span><input aria-label="Upload a product photo" type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>setFile(e.target.files?.[0]||null)}/></label><label>What is the photo for?<textarea rows={3} value={description} onChange={e=>setDescription(e.target.value)} maxLength={4000}/></label><button className="primary" disabled={!file||busy} onClick={scorePhoto}><ProductIcon name="spark"/>Analyze photo</button><p className="field-help">Pixel measurements are calculated locally. AI feedback is included when live generation is available.</p></section><section className="photo-results">{images.length?images.slice().reverse().map(img=><article className="product-card photo-result" key={img.id}><div className="photo-result-heading"><h3>{img.filename}</h3><SourceBadge value={img.result.provenance}/></div>{img.previewUrl&&<img className="reviewed-photo" src={img.previewUrl} alt={img.filename}/>}<div className="photo-score-line"><strong>{img.result.model?img.result.model.overall:img.result.local.technical_readiness}<small>/100</small></strong><span>{img.result.model?"AI photo assessment":"Technical photo readiness"}<small>{img.result.local.width} × {img.result.local.height} pixels</small></span></div>{img.result.model&&<div className="photo-feedback"><h4>What to improve</h4><ul>{img.result.model.fixes.map((fix,i)=><li key={i}>{fix}</li>)}</ul></div>}<div className="color-palette">{img.result.local.dominant_colors.map((color,i)=><span key={i} style={{background:color}} title={color}/>)}</div><p className="field-help">Scores are review suggestions, not a prediction of sales.</p></article>):<EmptyState icon="image" title="Your photo review will appear here">Upload an image to see its measurements, colors and improvement suggestions.</EmptyState>}</section></div>}

   {view==="audit"&&(campaign?<><div className="result-intro"><SourceBadge value={campaign.provenance}/><span>Based on the business brief you provided</span></div><div className="strategy-grid"><section className="product-card"><span className="small-label">YOUR OFFER</span><h2>What customers can come to you for</h2><p className="strategy-copy">{campaign.audit.analysis.offer_summary}</p></section><section className="product-card"><span className="small-label">AUDIENCE TO TEST</span><h2>Who this could resonate with</h2><p className="strategy-copy">{campaign.audit.analysis.audience_guess}</p><span className="quiet-label">A positioning hypothesis to review</span></section></div><section className="product-card"><div className="section-heading"><h2>Opportunities to work on</h2></div><div className="opportunity-list">{campaign.audit.analysis.gaps.map((gap,i)=><article key={i}><span>{String(i+1).padStart(2,"0")}</span><div><p>{gap.finding}</p><small>{gap.assumption?"Suggestion based on an assumption":"Based on your supplied business description"}</small></div></article>)}</div></section><section className="product-card"><h2>Directions for your campaign</h2><div className="positioning-grid">{campaign.audit.analysis.positioning_angles.map((angle,i)=><article key={i}><span>Direction {i+1}</span><p>{angle}</p></article>)}</div><div className="card-footer"><button className="primary" onClick={()=>onNavigate("campaign")}>Open campaign calendar<ProductIcon name="arrow"/></button><details className="subtle-details"><summary>Sources & assumptions</summary>{campaign.audit.evidence.map(e=><div className="source-note" key={e.id}><b>{e.id} · {e.type==="retrieved_public_page"?"Retrieved website evidence":e.type==="fixture"?"Sample fixture":"Your supplied content"}</b><p>{e.text||e.url}</p><small>Source presence does not prove the claim</small></div>)}</details></div></section></>:needCampaign)}

   {view==="campaign"&&(campaign?<><div className="collection-toolbar"><div className="filter-tabs" aria-label="Filter campaign posts">{["all",...new Set(campaign.items.map(i=>i.platform))].map(platform=><button key={platform} className={platformFilter===platform?"selected":""} onClick={()=>setPlatformFilter(platform)}>{platform==="all"?"All posts":platformName(platform)}</button>)}</div><button className="secondary" onClick={()=>onNavigate("audit")}>View strategy<ProductIcon name="arrow" size={16}/></button></div><section className="product-card campaign-sheet-card"><div className="campaign-sheet-heading"><div><strong>{campaign.duration_days||campaign.items.length}-day content plan</strong><span>{campaign.items.length} editable posts · {new Set(campaign.items.map(item=>item.platform)).size} platforms</span></div><SourceBadge value={campaign.provenance}/></div><div className="campaign-table-scroll"><table className="campaign-sheet"><thead><tr><th>Day / status</th><th>Platform</th><th>Format</th><th>Caption</th><th>Hashtags</th><th>Call to action</th><th>Image guidance</th><th>Image prompt</th><th>Reel / video script</th><th>Actions</th></tr></thead><tbody>{campaign.items.filter(item=>platformFilter==="all"||item.platform===platformFilter).map(item=><tr className="campaign-sheet-row" key={item.id}><td><strong>Day {item.day}</strong><small className={`sheet-state state-${item.state}`}>{item.state==="proposed"?"Draft":item.state}</small><SourceBadge value={item.provenance}/></td><td>{platformName(item.platform)}</td><td>{item.post_type}</td><td><div className="sheet-cell-text">{item.caption}</div></td><td><div className="sheet-cell-text">{item.hashtags.join(" ")}</div></td><td><div className="sheet-cell-text">{item.cta}</div></td><td><div className="sheet-cell-text">{item.creative_brief}</div></td><td><div className="sheet-cell-text">{item.image_prompt}</div></td><td><div className="sheet-cell-text">{item.video_script||"Not a video format"}</div></td><td><div className="sheet-actions"><button className="icon-button" aria-label={`Copy day ${item.day} caption`} onClick={()=>copy(item.caption+"\n\n"+item.hashtags.join(" "))}><ProductIcon name="copy" size={18}/></button><button className="icon-button" aria-label={`Edit day ${item.day} post`} disabled={item.state!=="proposed"} onClick={()=>editPost(item)}><ProductIcon name="edit" size={18}/></button><button className="text-link" onClick={()=>action(async()=>{await openCreativeItem(item.id);onNavigate("creatives")})}>Create or view visuals<ProductIcon name="arrow" size={15}/></button></div></td></tr>)}</tbody></table></div><p className="field-help">Review every field before use. Drafts are saved to this workspace; nothing is automatically published.</p></section></>:needCampaign)}
   {view==="creatives"&&(campaign?<div className="creative-layout"><section className="product-card creative-controls"><h2>Create a visual</h2><label>Choose campaign day<select value={itemId} disabled={busy} onChange={e=>{const id=e.target.value;action(()=>openCreativeItem(id))}}>{campaign.items.map(i=><option key={i.id} value={i.id}>Day {i.day} · {i.platform}</option>)}</select></label><label>Look & feel<input value={brandMood} onChange={e=>setBrandMood(e.target.value)} placeholder="For example: warm, minimal and handcrafted"/></label><label>Number of concepts<select value={requestedVariants} onChange={e=>setRequestedVariants(Number(e.target.value))}><option value={1}>1 concept</option><option value={2}>2 concepts</option><option value={3}>3 concepts</option></select></label><div className="creative-brief"><span className="small-label">VISUAL BRIEF</span><p>{campaign.items.find(i=>i.id===itemId)?.creative_brief}</p></div><button className="primary wide" disabled={busy} onClick={createVariants}><ProductIcon name="spark"/>Generate visuals</button><p className="field-help">New images use Meta AI credits. Opening saved images uses no credits.</p></section><section className="creative-results"><div className="section-heading"><h2>Your visuals</h2><span>{variants.length} saved {variants.length===1?"concept":"concepts"}</span></div>{variants.length?<div className="visual-grid">{variants.map(v=><article className={`visual-card studio-creative ${v.selected?"chosen":""}`} key={v.id}><div className="visual-image">{variantImages[v.id]?<img src={variantImages[v.id]} alt="Campaign creative"/>:<div className="image-loading"><span className="spinner"/>Loading saved image…</div>}{v.selected&&<span className="selected-ribbon"><ProductIcon name="check" size={14}/>Selected</span>}</div><div className="visual-card-body"><SourceBadge value={v.provenance}/><div className="visual-score"><div><span>Photo readiness</span><b>{v.scores.local.technical_readiness}<small>/100</small></b></div>{v.scores.brief_match&&<div><span>Brief match</span><b>{v.scores.brief_match.brief_match}<small>/100</small></b></div>}</div><button className={v.selected?"secondary wide":"primary wide"} disabled={busy||v.selected} onClick={()=>pickVariant(v)}>{v.selected?<><ProductIcon name="check" size={16}/>Selected for this campaign</>:"Use this concept"}</button></div></article>)}</div>:<EmptyState icon="image" title="Your next visual starts here">Choose a campaign day and a look, then generate a concept to review.</EmptyState>}</section></div>:needCampaign)}

   {view==="landing"&&(campaign?<>{page?<><div className="landing-toolbar"><div><span className={`review-state ${page.published?"state-approved":"state-proposed"}`}>{page.published?"Published":"Draft"}</span><SourceBadge value={page.provenance}/></div><div className="button-row"><button className="secondary" onClick={()=>{setLandingFields({headline:page.spec.headline,subheadline:page.spec.subheadline,offer:page.spec.offer});setEditLanding(true)}} disabled={busy||(!!landingReview&&landingReview.state!=="proposed")}><ProductIcon name="edit" size={16}/>Edit copy</button><button className="secondary" onClick={()=>download(`/api/v1/landing/${page.id}/export?workspace_id=${encodeURIComponent(workspace)}`,"sentinelx-landing.html")}><ProductIcon name="download" size={16}/>Download HTML</button>{landingApproved?<button className="primary" disabled={busy} onClick={()=>publish(!page.published)}><ProductIcon name="globe" size={16}/>{page.published?"Unpublish page":"Publish page"}</button>:<button className="primary" onClick={()=>onNavigate("approvals")}>Review before publishing<ProductIcon name="arrow" size={16}/></button>}</div></div><div className="landing-editor-layout"><div className="landing-browser product-card"><div className="preview-browser-bar"><span/><span/><span/><small>{page.published?"Published landing page":"Landing page preview"}</small><button className="icon-button" aria-label="Expand landing preview" onClick={()=>setExpandedPreview(true)}><ProductIcon name="landing" size={16}/></button></div>{preview?<iframe title="Landing preview" srcDoc={preview} sandbox="" referrerPolicy="no-referrer"/>:<div className="image-loading">Loading your page…</div>}</div><aside className="landing-side product-card"><span className="small-label">PAGE DETAILS</span><h2>{page.spec.business_name}</h2><p>{page.spec.headline}</p><dl><div><dt>Template</dt><dd>{page.spec.theme}</dd></div><div><dt>Status</dt><dd>{page.published?"Published":"Unpublished draft"}</dd></div><div><dt>Customer inquiries</dt><dd>{page.leads_count}</dd></div></dl>{page.published&&<a className="secondary button-link" href={page.url} target="_blank" rel="noreferrer"><ProductIcon name="globe" size={16}/>Open public page</a>}<button className="secondary wide" onClick={()=>action(async()=>{setLeads(await api<Lead[]>(`/api/v1/landing/${page.id}/leads?workspace_id=${encodeURIComponent(workspace)}`));setShowInquiries(true)})}>View inquiries</button><details className="subtle-details"><summary>Create another page</summary><label>Template<select value={pageTheme} onChange={e=>setPageTheme(e.target.value)}><option value="modern">Modern</option><option value="warm">Warm</option><option value="bold">Bold</option></select></label><label>Business WhatsApp<input value={whatsapp} onChange={e=>setWhatsapp(e.target.value)} placeholder="+919876543210"/></label><button className="primary wide" disabled={busy} onClick={createLanding}>Generate new page</button></details>{landingPages.length>1&&<label>Saved pages<select aria-label="Saved landing pages" value={page.id} onChange={e=>action(async()=>{const next=landingPages.find(p=>p.id===e.target.value);if(next){setPage(next);await loadPreview(next.id)}})}>{landingPages.map(p=><option key={p.id} value={p.id}>{p.spec.headline}</option>)}</select></label>}<p className="field-help">Reviewed copy must be reopened from Review & export before it can be edited.</p></aside></div></>:<section className="product-card landing-start"><span className="empty-icon"><ProductIcon name="landing" size={32}/></span><h2>Give your campaign a destination</h2><p>Create an editable page using your business brief and selected campaign visual.</p><div className="field-grid"><label>Business name<input value={businessName} onChange={e=>setBusinessName(e.target.value)}/></label><label>Page style<select value={pageTheme} onChange={e=>setPageTheme(e.target.value)}><option value="modern">Modern</option><option value="warm">Warm</option><option value="bold">Bold</option></select></label></div><label>Business WhatsApp <span className="optional">optional</span><input value={whatsapp} onChange={e=>setWhatsapp(e.target.value)} placeholder="+919876543210"/></label><button className="primary" disabled={busy} onClick={createLanding}><ProductIcon name="spark"/>Generate page draft</button><small>Starts as a private draft. You review it before publishing.</small></section>}</>:needCampaign)}

   {view==="approvals"&&(campaign?<><div className="review-toolbar"><div className="filter-tabs" aria-label="Review status">{["proposed","approved","rejected"].map(state=><button key={state} className={reviewFilter===state?"selected":""} onClick={()=>setReviewFilter(state)}>{state==="proposed"?"Needs review":state[0].toUpperCase()+state.slice(1)}<span>{board.filter(a=>a.state===state).length}</span></button>)}</div><button className="primary" disabled={approved===0||busy} onClick={()=>download(`/api/v1/campaigns/${campaign.id}/export?workspace_id=${encodeURIComponent(workspace)}&format=zip`,"sentinelx-approved-pack.zip")}><ProductIcon name="download" size={17}/>Download approved pack</button></div><section className="product-card review-list">{board.filter(a=>a.state===reviewFilter).length?board.filter(a=>a.state===reviewFilter).map(a=><article className="review-list-row studio-review" key={a.id}><span className="review-type-icon"><ProductIcon name={a.target_kind==="landing"?"landing":a.target_kind==="creative"?"image":"campaign"}/></span><button className="review-item-copy" onClick={()=>setReviewItem(a)}><small>{a.target_kind==="campaign_item"?"SOCIAL POST":a.target_kind==="landing"?"LANDING PAGE":"CAMPAIGN VISUAL"}</small><h3>{a.title}</h3><p>{a.description}</p></button><div className="review-row-actions">{a.state==="proposed"?<><button className="secondary" disabled={busy} onClick={()=>setReviewItem(a)}>Review</button><button className="approve-button" aria-label={`Approve ${a.title}`} disabled={busy} onClick={()=>decide(a,"approved")}><ProductIcon name="check" size={17}/>Approve</button></>:<button className="secondary" disabled={busy} onClick={()=>decide(a,"reopen")}>Reopen</button>}</div></article>):<EmptyState icon="review" title={reviewFilter==="proposed"?"Nothing waiting for review":"No items here yet"}>Reviewed items move into their matching tab. Only approved deliverables go into the download pack.</EmptyState>}</section><p className="field-help review-footnote">Approvals record your decision. Publishing a landing page is a separate action; social accounts are not automatically posted to.</p></>:needCampaign)}
   {editor&&<Modal title={`Edit day ${editor.day} post`} wide onClose={()=>setEditor(null)}><form className="campaign-post-editor" onSubmit={e=>{e.preventDefault();savePost()}}><label>Caption<textarea autoFocus required rows={4} minLength={10} maxLength={1500} value={editFields.caption} onChange={e=>setEditFields(old=>({...old,caption:e.target.value}))}/></label><label>Hashtags <span className="optional">separate with spaces, commas or new lines</span><textarea rows={2} maxLength={500} value={editFields.hashtags} onChange={e=>setEditFields(old=>({...old,hashtags:e.target.value}))}/></label><label>Call to action<input required minLength={5} maxLength={180} value={editFields.cta} onChange={e=>setEditFields(old=>({...old,cta:e.target.value}))}/></label><label>Image guidance<textarea required rows={3} minLength={10} maxLength={600} value={editFields.creative_brief} onChange={e=>setEditFields(old=>({...old,creative_brief:e.target.value}))}/></label><label>Image prompt<textarea required rows={4} minLength={15} maxLength={1000} value={editFields.image_prompt} onChange={e=>setEditFields(old=>({...old,image_prompt:e.target.value}))}/></label><PromptVoiceInput token={token} workspace={workspace} available={Boolean(runtime?.live_enabled&&!sampleMode)} onTranscript={text=>setEditFields(old=>({...old,image_prompt:[old.image_prompt.trimEnd(),text].filter(Boolean).join(" ")}))}/><label>Reel / video script <span className="optional">if this is not a video, leave blank</span><textarea rows={4} maxLength={1800} value={editFields.video_script} onChange={e=>setEditFields(old=>({...old,video_script:e.target.value}))}/></label><div className="form-actions"><button type="button" className="secondary" onClick={()=>setEditor(null)}>Cancel</button><button className="primary" disabled={busy}>Save post</button></div></form></Modal>}
   {editLanding&&<Modal title="Edit landing page copy" onClose={()=>setEditLanding(false)}><form onSubmit={e=>{e.preventDefault();savePage()}}>{(["headline","subheadline","offer"] as const).map(field=><label key={field}>{field==="headline"?"Headline":field==="subheadline"?"Introduction":"Offer"}<textarea autoFocus={field==="headline"} required rows={field==="headline"?2:3} value={landingFields[field]} onChange={e=>setLandingFields(old=>({...old,[field]:e.target.value}))}/></label>)}<div className="form-actions"><button type="button" className="secondary" onClick={()=>setEditLanding(false)}>Cancel</button><button className="primary" disabled={busy}>Save changes</button></div></form></Modal>}
   {reviewItem&&<Modal title="Review deliverable" onClose={()=>setReviewItem(null)}><div className="review-modal-content"><span className="small-label">{reviewItem.target_kind.replaceAll("_"," ")}</span><h3>{reviewItem.title}</h3><p>{campaign?.items.find(i=>i.id===reviewItem.target_id)?.caption||reviewItem.description}</p><label>Review note <span className="optional">optional</span><textarea rows={2} maxLength={500} value={reviewNote} onChange={e=>setReviewNote(e.target.value)} placeholder="Add feedback or the reason for your decision"/></label><div className="form-actions">{reviewItem.state==="proposed"?<><button className="secondary reject-button" disabled={busy} onClick={()=>decide(reviewItem,"rejected")}>Reject</button><button className="primary" disabled={busy} onClick={()=>decide(reviewItem,"approved")}><ProductIcon name="check" size={17}/>Approve deliverable</button></>:<button className="secondary" disabled={busy} onClick={()=>decide(reviewItem,"reopen")}>Reopen review</button>}</div></div></Modal>}
   {showInquiries&&<Modal title="Customer inquiries" onClose={()=>setShowInquiries(false)}>{leads.length?leads.map(lead=><article className="inquiry-row" key={lead.id}><h3>{lead.name}</h3><a href={`tel:${lead.phone}`}>{lead.phone}</a><p>{lead.message}</p><small>{new Date(lead.created_at).toLocaleDateString()}</small></article>):<EmptyState icon="report" title="No inquiries yet">When someone submits the form on your published page, their inquiry will appear here.</EmptyState>}</Modal>}
   {expandedPreview&&<Modal title="Landing page preview" wide onClose={()=>setExpandedPreview(false)}><iframe title="Expanded landing preview" className="expanded-page-preview" srcDoc={preview} sandbox="" referrerPolicy="no-referrer"/></Modal>}
   {busy&&<div className="task-indicator" role="status" aria-live="polite"><span className="spinner"/><div><strong>{activity}</strong><small>Your work will be saved in this workspace.</small></div></div>}
 </section>;
}
