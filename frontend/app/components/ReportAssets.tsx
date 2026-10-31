"use client";
import AIText from "./AIText";
import VoiceTextarea from "./VoiceTextarea";
import {useEffect,useState} from "react";
import {SourceBadge,ProductIcon} from "./ProductUI";
const BASE=process.env.NEXT_PUBLIC_API_URL??"";
type Asset={id:string;kind:string;filename:string;provenance:string;text:string;limitation:string;status:string};
export default function ReportAssets({token,workspace,mission,mode}:{token:string;workspace:string;mission:string;mode:"live"|"sample"}){
 const [assets,setAssets]=useState<Asset[]>([]);const [file,setFile]=useState<File|null>(null);
 const [consent,setConsent]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState("");
 const [kind,setKind]=useState("business_brief");const [instructions,setInstructions]=useState("");
 const scope="?workspace_id="+encodeURIComponent(workspace);
 const root="/api/v1/missions/"+mission;
 async function load(){const response=await fetch(BASE+root+"/assets"+scope,{headers:{Authorization:"Bearer "+token}});if(!response.ok)throw Error("Could not load assets");setAssets(await response.json())}
 useEffect(()=>{setAssets([]);setFile(null);setError("");load().catch(()=>setError("Could not load saved media reviews and documents."))},[mission,workspace,token]);
 async function send(path:string,body:BodyInit,isJson=false){
  setBusy(true);setError("");
  try{const response=await fetch(BASE+root+path,{method:"POST",headers:{Authorization:"Bearer "+token,...(isJson?{"Content-Type":"application/json"}:{})},body});
   const data=await response.json();if(!response.ok)throw Error(typeof data.detail==="string"?data.detail:`Request failed (${response.status})`);await load();
  }catch(error){setError(error instanceof Error?error.message:"Request failed")}
  finally{setBusy(false)}
 }
 async function review(){if(!file)return;if(file.size>5_000_000){setError("Use a file of at most 5 MB.");return}const form=new FormData();form.append("workspace_id",workspace);form.append("file",file);form.append("consent",String(consent));form.append("generation_mode",mode);await send("/media",form)}
 async function download(asset:Asset,format:"md"|"html"){
  try{const response=await fetch(BASE+root+"/document/"+asset.id+scope+"&format="+format,{headers:{Authorization:"Bearer "+token}});if(!response.ok)throw Error();const url=URL.createObjectURL(await response.blob());const link=document.createElement("a");link.href=url;link.download="sentinelx-"+asset.kind+"."+format;link.click();URL.revokeObjectURL(url)}catch{setError("Download unavailable")}
 }
 return <section className="product-card report-assets"><h2>Images, video & documents</h2><p className="section-description">Add an explicit media review to this report or create a business document from its evidence. Each new live review or document uses one budgeted request. Opening saved work uses no credits.</p>
 {error&&<div className="product-notice notice-error" role="alert">{error}</div>}
 <div className="report-asset-grid"><section><h3>Review media</h3><label>Upload an image, short MP4 or PDF<input aria-label="Report media file" type="file" accept="image/png,image/jpeg,image/webp,video/mp4,application/pdf" onChange={event=>setFile(event.target.files?.[0]||null)}/></label><p className="field-help">At most 5 MB. Only the file you provide is inspected. PDF and MP4 use a documented adapter that has not yet been verified with your live account. Audio completeness is not guaranteed.</p><label className="checkbox-label"><input type="checkbox" checked={consent} onChange={event=>setConsent(event.target.checked)}/>I can share this file with the model for review.</label><button className="secondary" disabled={busy||!file||!consent} onClick={review}>{busy?"Processing…":"Review uploaded media"}</button></section>
 <section><h3>Create a document</h3><label>Document type<select value={kind} onChange={event=>setKind(event.target.value)}><option value="business_brief">Business brief</option><option value="inquiry_checklist">Customer inquiry checklist</option><option value="video_script">Video shooting script (text)</option></select></label><VoiceTextarea label="Additional instructions" token={token} workspace={workspace} available={mode==="live"} rows={2} maxLength={600} value={instructions} onChange={setInstructions} placeholder="Audience, purpose or language"/><button className="primary" disabled={busy} onClick={()=>send("/documents",JSON.stringify({workspace_id:workspace,kind,instructions,generation_mode:mode}),true)}><ProductIcon name="report" size={17}/>Create document</button><p className="field-help">Download Markdown or a printable HTML document. A shooting script is not a rendered video. Video generation is unavailable through the verified integration.</p></section></div>
 {assets.map(asset=><article className="report-asset" key={asset.id}><div className="section-heading"><h3>{asset.filename||asset.kind.replaceAll("_"," ")}</h3><SourceBadge value={asset.provenance}/></div><p className="field-help">{asset.limitation}</p><AIText text={asset.text}/><div className="button-row"><button className="secondary compact" onClick={()=>download(asset,"md")}>Download Markdown</button><button className="secondary compact" onClick={()=>download(asset,"html")}>Download printable HTML</button></div></article>)}
 </section>;
}
