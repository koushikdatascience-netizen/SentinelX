"use client";
import {useEffect,useState} from "react";
const API=process.env.NEXT_PUBLIC_API_URL ?? "";
type Model={name:string;capability:string;stage:string;live_tested:boolean};
async function upload(url:string,file:File,token:string){const body=new FormData();body.append("file",file);const r=await fetch(API+url,{method:"POST",headers:{Authorization:"Bearer "+token},body});const data=await r.json();if(!r.ok)throw new Error(typeof data.detail==="string"?data.detail:"Upload failed");return data;}
export default function MediaAndModels({token}:{token:string}){
 const [image,setImage]=useState<File|null>(null),[audio,setAudio]=useState<File|null>(null);
 const [imageResult,setImageResult]=useState<Record<string,unknown>|null>(null),[audioResult,setAudioResult]=useState<Record<string,unknown>|null>(null);
 const [models,setModels]=useState<Model[]>([]),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 useEffect(()=>{fetch(API+"/api/v1/meta/readiness",{headers:{Authorization:"Bearer "+token}}).then(r=>r.ok?r.json():Promise.reject(Error("Model readiness unavailable"))).then(x=>setModels(x.integrations||[])).catch(()=>{});},[token]);
 async function run(type:"image"|"audio"){const file=type==="image"?image:audio;if(!file)return;setBusy(true);setError("");try{const result=await upload(type==="image"?"/api/v1/media/image/inspect":"/api/v1/media/voice/transcribe",file,token);if(type==="image")setImageResult(result);else setAudioResult(result);}catch(e){setError(e instanceof Error?e.message:"Upload failed")}finally{setBusy(false)}}
 return <section className="media-suite">
  <div className="media-head"><div><span className="eyebrow">MULTIMODAL WORKBENCH</span><h3>Image & voice intake</h3><p className="muted">Securely validate inputs now. Live segmentation and transcription remain off until provider access and billing are verified.</p></div><span className="status neutral">Safe development</span></div>
  <div className="media-grid"><div className="upload-card"><div className="upload-icon">▧</div><h4>Product image inspection</h4><p className="muted">PNG, JPEG or WebP. Up to 5 MB. Reports dimensions and format—not object recognition.</p><label className="file-input">Choose image<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>setImage(e.target.files?.[0]||null)}/></label>{image&&<small>{image.name}</small>}<button className="secondary wide" disabled={busy||!image} onClick={()=>run("image")}>Validate image</button>{imageResult&&<div className="media-result"><b>Validated locally</b><pre>{JSON.stringify(imageResult,null,2)}</pre></div>}</div>
  <div className="upload-card"><div className="upload-icon">◉</div><h4>Voice instruction intake</h4><p className="muted">Upload a short WAV, MP3, OGG or WebM recording. No transcription occurs in demo mode.</p><label className="file-input">Choose recording<input type="file" accept="audio/wav,audio/mpeg,audio/ogg,audio/webm,audio/mp4" onChange={e=>setAudio(e.target.files?.[0]||null)}/></label>{audio&&<small>{audio.name}</small>}<button className="secondary wide" disabled={busy||!audio} onClick={()=>run("audio")}>Check voice pipeline</button>{audioResult&&<div className="media-result"><b>Provider response</b><pre>{JSON.stringify(audioResult,null,2)}</pre></div>}</div></div>
  {error&&<div className="alert error" role="alert">{error}</div>}
  <div className="integration-list"><div className="media-head"><h3>Meta model integration tracker</h3><small className="muted">No false claims of model use</small></div>{models.map(m=><div className="integration-row" key={m.name}><span><b>{m.name}</b><small>{m.capability.replaceAll("_"," ")}</small></span><span className="status neutral">{m.stage.replaceAll("_"," ")}</span></div>)}</div>
 </section>
}
