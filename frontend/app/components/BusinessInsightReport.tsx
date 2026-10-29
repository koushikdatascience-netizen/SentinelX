"use client";
import {useState} from "react";

export type BusinessFinding={source_id:string;quote:string;observation:string;why:string;next_step:string;area?:string;priority?:string;verification?:string};
export type BusinessInsights={summary?:string;strengths:BusinessFinding[];improvements:BusinessFinding[];unknowns:string[]};
type Source={id:string;text?:string;url?:string;title?:string;origin?:string;filename?:string};
const areas:Record<string,string>={positioning:"Positioning",products_services:"Products & services",contact_journey:"Contact journey",content:"Website content",other:"General"};
const priorities:Record<string,number>={high:0,medium:1,low:2,not_ranked:3};

export default function BusinessInsightReport({data,sources,business,date,visualReviewed,onSources}:{data:BusinessInsights;sources:Source[];business:string;date:string;visualReviewed:boolean;onSources:()=>void}){
 const [view,setView]=useState("improvements");
 const improvements=[...data.improvements].sort((a,b)=>(priorities[a.priority||"not_ranked"]??3)-(priorities[b.priority||"not_ranked"]??3));
 function exportReport(){
  const lines=[`# ${business} — business improvement report`,new Date(date).toLocaleString(),"Meta AI interpretation · source quotes validated · owner review required.",data.summary||"",`Visual review: ${visualReviewed?"Available separately in the saved research run":"Not available; text findings do not establish visual quality"}.`];
  for(const [title,items] of [["Recommended improvements",improvements],["Preserve what works",data.strengths]] as const){
   lines.push(`\n## ${title}`);
   for(const item of items){const source=sources.find(s=>s.id===item.source_id);lines.push(`\n### ${item.observation}`,`Priority: ${item.priority||"not ranked"} · ${areas[item.area||"other"]||"General"}`,`Why: ${item.why}`,`Next step: ${item.next_step}`,`Verify: ${item.verification||"Define an acceptance check before making this change."}`,`Evidence (${item.source_id}): ${item.quote}`,`Source: ${source?.url||source?.filename||"Owner-supplied details"}`);}
  }
  lines.push("\n## Unknowns",...data.unknowns.map(item=>"- "+item),"\nRecommendations are hypotheses. No edits were published or business outcomes measured.");
  const url=URL.createObjectURL(new Blob([lines.join("\n\n")],{type:"text/markdown;charset=utf-8"}));const link=document.createElement("a");link.href=url;link.download="sentinelx-business-improvement-report.md";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 function finding(item:BusinessFinding,index:number){const source=sources.find(s=>s.id===item.source_id);return <article className="insight-action" key={`${item.source_id}-${index}`}>
  <div className="insight-labels"><span>{areas[item.area||"other"]||"General"}</span>{item.priority&&item.priority!=="not_ranked"&&<span className={`insight-priority priority-${item.priority}`}>{item.priority} priority · AI suggested</span>}</div>
  <h3>{item.observation}</h3><p><strong>Why it matters</strong>{item.why}</p><p><strong>{view==="strengths"?"Keep or build on this":"Recommended change"}</strong>{item.next_step}</p>
  <p><strong>How to verify</strong>{item.verification||"No verification check was saved in this older report. Define acceptance criteria before making changes."}</p>
  <details><summary>View supporting evidence · {item.source_id}</summary><blockquote>{item.quote}</blockquote><p className="field-help">Quote matched to saved text. This verifies the citation, not the business claim or predicted benefit.</p>{source?.url&&/^https:\/\//i.test(source.url)?<a href={source.url} target="_blank" rel="noreferrer">{source.title||source.url} ↗</a>:<small>{source?.filename||"Owner-supplied details — unverified"}</small>}</details>
 </article>}
 return <section className="business-insight-report" aria-label="Business improvement report">
  <header className="insight-report-head"><div><span className="page-kicker">FROM EVIDENCE TO IMPROVEMENT</span><h2>Your business improvement report</h2><p>{data.summary||"Review what to preserve, which changes to prioritize, and the evidence behind each recommendation."}</p><small>Meta AI generated · {new Date(date).toLocaleDateString()} · owner review required</small></div><button className="secondary" onClick={exportReport}>Download report</button></header>
  <div className="insight-report-stats"><span><strong>{data.improvements.length}</strong>recommended changes</span><span><strong>{data.strengths.length}</strong>strengths to preserve</span><span><strong>{sources.length}</strong>saved text sources</span></div>
  <p className="field-help">Priorities are recommendations, not measured impact. {visualReviewed?"A separate visual review appears below.":"Visual review is unavailable for this run. These findings do not assess screenshot colors, layout or image quality."}</p>
  <div className="business-tabs" role="group" aria-label="Insight report views">{[["improvements","Improvement plan"],["strengths","What works"],["unknowns","Gaps & verification"]].map(([id,label])=><button key={id} aria-pressed={view===id} onClick={()=>setView(id)}>{label}</button>)}</div>
  {view==="unknowns"?<section className="product-card"><h3>What still needs checking</h3><ul>{data.unknowns.map((item,index)=><li key={index}>{item}</li>)}</ul><p>Collected pages may be incomplete. Search results do not establish competitor identity. No performance, conversion or revenue improvement has been measured.</p><button className="secondary" onClick={onSources}>Inspect collected sources</button></section>:<div className="insight-action-list">{(view==="strengths"?data.strengths:improvements).map(finding)}{!(view==="strengths"?data.strengths:improvements).length&&<p>No source-supported findings in this section.</p>}</div>}
 </section>;
}
