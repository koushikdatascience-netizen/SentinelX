"use client";
import {useEffect,useRef,useState} from "react";
import {ProductIcon,SourceBadge} from "./ProductUI";

const BASE=process.env.NEXT_PUBLIC_API_URL??"";
type Check={name:string;passed:boolean;detail:string;source_id?:string};
type Mission={id:string;goal:string;status:string;provenance:string;error?:string;
 sources:{id:string;url:string;title:string;text:string;role:string;origin:string;collected_at:string|null;sha256:string|null}[];
 checks:Check[];trace:{agent:string;kind:string;status:string;result?:string;duration_ms?:number}[];
 plan:{summary:string;opportunities:{title:string;source_id:string;quote:string;hypothesis:string;proposed_action:string;success_check:string}[];unknowns:string[]}|null;
 limitations:string[];verification:{passed:boolean;checks:Check[];next_step:string;url:string;checked_at:string;
 before_after:{measurement:string;source_page:number|boolean|null;published_page:number|boolean}[];suggested_corrections:string[]}|null};
type Saved={id:string;goal:string;status:string};
type Page={id:string;campaign_id:string;published:boolean;spec:{headline:string};provenance:string};

export default function BusinessMission({token,workspace,website,goal,mode,onSample,onDashboard,onCampaign,onLanding}:{
 token:string;workspace:string;website:string;goal:string;mode:"sample"|"live";onSample:(sample:boolean)=>void;
 onDashboard:()=>void;onCampaign:(id:string,goal:string,website:string,description:string)=>void;onLanding:()=>void}){
 const [url,setUrl]=useState(website);const [objective,setObjective]=useState(goal);
 const [competitors,setCompetitors]=useState("");const [consent,setConsent]=useState(false);
 const [busy,setBusy]=useState(false);const [error,setError]=useState("");
 const [mission,setMission]=useState<Mission|null>(null);const [saved,setSaved]=useState<Saved[]>([]);
 const [pending,setPending]=useState("");const [pages,setPages]=useState<Page[]>([]);const [pageId,setPageId]=useState("");
 const [testConsent,setTestConsent]=useState(false);
 const request=useRef<{signature:string;id:string}|null>(null);
 async function api<T>(path:string,method="GET",body?:unknown):Promise<T>{
  const response=await fetch(BASE+path,{method,headers:{Authorization:"Bearer "+token,"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined,cache:"no-store"});
  const data=await response.json();
  if(!response.ok)throw Error(typeof data.detail==="string"?data.detail:data.detail?.message||`Request failed (${response.status})`);
  return data;
 }
 const scope="?workspace_id="+encodeURIComponent(workspace);
 async function open(id:string){setError("");setPageId("");setMission(await api<Mission>("/api/v1/missions/"+id+scope))}
 async function history(){const rows=await api<Saved[]>("/api/v1/missions"+scope);setSaved(rows);return rows}
 useEffect(()=>{
  let active=true;
  api<Saved[]>("/api/v1/missions"+scope).then(async rows=>{
   if(!active)return;setSaved(rows);
   if(rows[0]){const result=await api<Mission>("/api/v1/missions/"+rows[0].id+scope);if(active)setMission(result)}
  }).catch(()=>{if(active)setError("Could not load saved missions.")});
  return()=>{active=false};
 },[workspace,token]);
 useEffect(()=>{
  if(!busy||!pending)return;
  const timer=setInterval(()=>{api<Mission>("/api/v1/missions/"+pending+scope).then(setMission).catch(()=>{})},2000);
  return()=>clearInterval(timer);
 },[busy,pending]);
 useEffect(()=>{
  if(!mission)return;let active=true;
  api<Page[]>("/api/v1/landing"+scope).then(async rows=>{
   const campaigns=await api<{id:string;mission_id?:string}[]>("/api/v1/campaigns"+scope);
   const linked=campaigns.filter(campaign=>campaign.mission_id===mission.id).map(campaign=>campaign.id);
   if(active)setPages(rows.filter(p=>linked.includes(p.campaign_id)));
  }).catch(()=>{if(active)setError("Could not load linked landing pages.")});
  return()=>{active=false};
 },[mission?.id]);
 async function run(event:React.FormEvent){
  event.preventDefault();setBusy(true);setError("");
  const inputs={workspace_id:workspace,website:url,goal:objective,competitors:competitors.split(/\n/).map(x=>x.trim()).filter(Boolean),consent_public_fetch:consent,generation_mode:mode};
  const signature=JSON.stringify(inputs);
  if(request.current?.signature!==signature)request.current={signature,id:crypto.randomUUID()};
  const id=request.current!.id;setPending(id);
  try{setMission(await api<Mission>("/api/v1/missions","POST",{...inputs,request_id:id}));await history()}
  catch(error){setError(error instanceof Error?error.message:"Mission failed");try{await open(id);await history()}catch{}}
  finally{setBusy(false);setPending("")}
 }
 async function verify(){
  if(!mission||!pageId)return;setBusy(true);setError("");
  try{
   const result=await api<NonNullable<Mission["verification"]>>("/api/v1/missions/"+mission.id+"/verify"+scope,"POST",{page_id:pageId,consent_synthetic_inquiry:testConsent});
   setMission(old=>old?{...old,verification:result}:old);
  }catch(error){setError(error instanceof Error?error.message:"Verification failed")}
  finally{setBusy(false)}
 }
 async function download(){
  if(!mission)return;
  try{
   const result=await api<Mission>("/api/v1/missions/"+mission.id+"/report"+scope);
   const object=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:"application/json"}));
   const link=document.createElement("a");link.href=object;link.download="sentinelx-mission.json";link.click();URL.revokeObjectURL(object);
  }catch{setError("Report download failed.")}
 }
 return <section className="dashboard-ui mission-ui">
  <button className="breadcrumb-back" onClick={onDashboard}><ProductIcon name="back" size={16}/>Dashboard</button>
  <div className="product-page-head"><div><div className="page-kicker">BUSINESS INTELLIGENCE → ACTION</div><h1>Business mission</h1><p>Inspect real sources, find a specific opportunity, prepare an improvement and verify its delivery.</p></div>
   {saved.length>0&&<label className="campaign-picker">Saved missions<select aria-label="Saved missions" disabled={busy} value={mission?.id||""} onChange={event=>open(event.target.value).catch(()=>setError("Could not open mission."))}>{saved.map(row=><option key={row.id} value={row.id}>{row.goal} · {row.status}</option>)}</select></label>}
  </div>
  {error&&<div className="product-notice notice-error" role="alert">{error}</div>}
  <div className="creation-layout mission-layout"><section className="product-card form-card"><h2>What should we improve?</h2>
   <form onSubmit={run}><label>Business website<input required type="url" value={url} onChange={event=>setUrl(event.target.value)} placeholder="https://your-business.com"/></label>
    <label>Business goal<textarea required minLength={10} maxLength={600} rows={3} value={objective} onChange={event=>setObjective(event.target.value)}/></label>
    <details className="subtle-details"><summary>Comparison websites (optional)</summary><label>Public comparison URLs<textarea rows={2} value={competitors} onChange={event=>setCompetitors(event.target.value)} placeholder="Up to two HTTPS URLs, one per line"/></label><p className="field-help">Only pages you specify are compared. SentinelX does not claim to discover the whole market.</p></details>
    <label className="checkbox-label"><input type="checkbox" checked={mode==="sample"} onChange={event=>onSample(event.target.checked)}/>Use sample mission (no network or credits)</label>
    <label className="checkbox-label"><input type="checkbox" required={mode==="live"} checked={consent} onChange={event=>setConsent(event.target.checked)}/>Inspect the supplied public pages and use one bounded Meta planning request.</label>
    <button className="primary wide" disabled={busy}><ProductIcon name="spark"/>{busy?"Working on your mission…":mode==="sample"?"Run sample mission":"Run business mission"}</button>
    <p className="field-help">Up to three pages. One AI request. Unchanged requests reuse their saved result; failures are never retried automatically.</p>
    {mission?.status==="failed"&&<button type="button" className="secondary" disabled={busy} onClick={()=>{request.current=null;setError("Ready for one new explicit attempt.")}}>Prepare a new attempt</button>}
   </form></section>
   <section className="product-card mission-trace"><h2>Execution trace</h2><p className="section-description">Real tool work and model reasoning are identified separately.</p>
    {!mission?.trace.length?<p className="muted">Start a mission to see its source collection, inspection, planning and verification handoffs.</p>:mission.trace.map((step,index)=><article className="mission-step" key={index}><span className={`mission-step-dot ${step.status}`}>{step.status==="completed"?<ProductIcon name="check" size={15}/>:index+1}</span><div><strong>{step.agent}</strong><small>{step.kind} · {step.status}{step.duration_ms!==undefined?` · ${(step.duration_ms/1000).toFixed(1)}s`:""}</small>{step.result&&<p>{step.result}</p>}</div></article>)}
    {mission&&<SourceBadge value={mission.provenance}/>}</section></div>
  {mission?.error&&<div className="product-notice notice-error">{mission.error}</div>}
  {mission?.plan&&<><section className="product-card"><div className="section-heading"><h2>The opportunity</h2><SourceBadge value={mission.provenance}/></div><p className="strategy-copy">{mission.plan.summary}</p>
   <div className="mission-opportunities">{mission.plan.opportunities.map((opportunity,index)=><article key={index}><span className="small-label">HYPOTHESIS · OWNER REVIEW REQUIRED</span><h3>{opportunity.title}</h3><p>{opportunity.hypothesis}</p><blockquote>{opportunity.quote}<small>Exact quote matched to {opportunity.source_id}</small></blockquote><h4>Proposed improvement</h4><p>{opportunity.proposed_action}</p><h4>How to verify delivery</h4><p>{opportunity.success_check}</p></article>)}</div>
   <div className="form-actions"><button className="secondary" onClick={download}><ProductIcon name="download" size={16}/>Download mission report</button><button className="primary" disabled={busy} onClick={()=>onCampaign(mission.id,mission.goal,mission.sources.find(source=>source.role==="business")?.url||url,mission.sources.find(source=>source.role==="business")?.text.slice(0,2400)||"")}>Prepare campaign from mission<ProductIcon name="arrow" size={17}/></button></div></section>
   <section className="product-card"><h2>Collected evidence & measured checks</h2><p className="section-description">An exact quote proves source matching. It does not independently prove a website’s claims or a business outcome.</p>
    {mission.sources.map(source=><details className="mission-source" key={source.id}><summary>{source.id} · {source.title||source.url} · {source.origin==="fixture"?"Sample fixture":"Retrieved public page"}</summary><a href={source.url} target="_blank" rel="noopener noreferrer">{source.url}</a><p>{source.collected_at?new Date(source.collected_at).toLocaleString():"No real retrieval"}</p>{source.sha256&&<small className="content-hash">SHA-256 {source.sha256}</small>}<blockquote>{source.text}</blockquote></details>)}
    <div className="mission-checks">{mission.checks.map((check,index)=><article key={index}><span className={check.passed?"check-pass":"check-review"}>{check.passed?"Observed":"Review"}</span><div><strong>{check.source_id} · {check.name}</strong><p>{check.detail}</p></div></article>)}</div>
   </section>
   <section className="product-card"><h2>Execute, then verify</h2><p className="section-description">Create a landing draft from this mission’s campaign. Review it, explicitly publish it, then check the public page and form. Approval alone never publishes it.</p>
    <button className="secondary" onClick={onLanding}>Open landing pages<ProductIcon name="arrow" size={16}/></button>
    {pages.length>0&&<div className="mission-verification-form"><label>Page from this mission<select aria-label="Page to verify" value={pageId} onChange={event=>setPageId(event.target.value)}><option value="">Choose a published page</option>{pages.map(page=><option key={page.id} value={page.id} disabled={!page.published}>{page.spec.headline} · {page.published?"published":"draft"}</option>)}</select></label><label className="checkbox-label"><input type="checkbox" checked={testConsent} onChange={event=>setTestConsent(event.target.checked)}/>Submit and remove one clearly labeled synthetic test inquiry. This is not a customer lead.</label><button className="primary" disabled={!pageId||!testConsent||busy} onClick={verify}>Verify public page & form</button></div>}
    {mission.verification&&<div className="mission-verification"><h3>{mission.verification.passed?"Technical delivery verified":"Changes need review"}</h3>{mission.verification.checks.map((check,index)=><p key={index}><b>{check.passed?"Pass":"Fail"} · {check.name}</b><span>{check.detail}</span></p>)}{mission.verification.before_after.length>0&&<table className="mission-comparison"><caption>Measured HTML signals · original page vs approved landing page</caption><thead><tr><th>Check</th><th>Original page</th><th>Landing page</th></tr></thead><tbody>{mission.verification.before_after.map(item=><tr key={item.measurement}><td>{item.measurement.replaceAll("_"," ")}</td><td>{String(item.source_page??"Unknown")}</td><td>{String(item.published_page)}</td></tr>)}</tbody></table>}<p>{mission.verification.next_step}</p>{mission.verification.suggested_corrections.map((text,index)=><p key={index}>{text}</p>)}<small>No sales or conversion improvement is claimed.</small></div>}
   </section><details className="subtle-details"><summary>Unknowns and limits</summary>{[...mission.plan.unknowns,...mission.limitations].map((text,index)=><p key={index}>{text}</p>)}</details>
  </>}
 </section>;
}
