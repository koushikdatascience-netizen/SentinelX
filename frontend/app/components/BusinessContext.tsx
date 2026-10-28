"use client";
import {useEffect,useRef,useState} from "react";
import {SourceBadge} from "./ProductUI";
const BASE=process.env.NEXT_PUBLIC_API_URL??"";
type Context={id:string;status:string;kind:string;filename:string;text:string;provenance:string;limitation:string};

function wav(samples:Float32Array){
 const bytes=new ArrayBuffer(44+samples.length*2),view=new DataView(bytes);
 function text(offset:number,value:string){for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i))}
 text(0,"RIFF");view.setUint32(4,36+samples.length*2,true);text(8,"WAVE");text(12,"fmt ");view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,24000,true);view.setUint32(28,48000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);text(36,"data");view.setUint32(40,samples.length*2,true);
 samples.forEach((sample,i)=>{const n=Math.max(-1,Math.min(1,sample));view.setInt16(44+i*2,n<0?n*32768:n*32767,true)});
 return new File([bytes],"voice-goal.wav",{type:"audio/wav"});
}

export default function BusinessContext({token,workspace,mode,onGoal,onSelect}:{token:string;workspace:string;mode:"sample"|"live";onGoal:(goal:string)=>void;onSelect:(ids:string[])=>void}){
 const [rows,setRows]=useState<Context[]>([]),[selected,setSelected]=useState<string[]>([]),[kind,setKind]=useState("business_twin");
 const [file,setFile]=useState<File|null>(null),[notes,setNotes]=useState(""),[consent,setConsent]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(""),[voice,setVoice]=useState(""),[recording,setRecording]=useState(false);
 const recorder=useRef<MediaRecorder|null>(null),stream=useRef<MediaStream|null>(null),timer=useRef<ReturnType<typeof setTimeout>|null>(null);
 const mounted=useRef(true);
 useEffect(()=>{let active=true;mounted.current=true;setRows([]);setSelected([]);onSelect([]);fetch(BASE+"/api/v1/business-context?workspace_id="+encodeURIComponent(workspace),{headers:{Authorization:"Bearer "+token}}).then(async r=>{if(!r.ok)throw Error();const data=await r.json();if(active)setRows(data)}).catch(()=>{if(active)setError("Could not load business context.")});return()=>{active=false;mounted.current=false;if(timer.current)clearTimeout(timer.current);if(recorder.current?.state==="recording")recorder.current.stop();stream.current?.getTracks().forEach(t=>t.stop())}},[workspace,token]);
 function choose(id:string){const ids=selected.includes(id)?selected.filter(value=>value!==id):[...selected,id].slice(-3);setSelected(ids);onSelect(ids)}
 async function capture(){
  if(recording){recorder.current?.stop();return}
  setError("");
  try{
   const input=await navigator.mediaDevices.getUserMedia({audio:true});if(!mounted.current){input.getTracks().forEach(track=>track.stop());return}stream.current=input;
   const chunks:BlobPart[]=[];const device=new MediaRecorder(input);recorder.current=device;
   device.ondataavailable=event=>{if(event.data.size)chunks.push(event.data)};
   device.onstop=async()=>{input.getTracks().forEach(track=>track.stop());if(timer.current)clearTimeout(timer.current);if(!mounted.current)return;setRecording(false);
    try{const audio=new AudioContext();let decoded:AudioBuffer;try{decoded=await audio.decodeAudioData(await new Blob(chunks,{type:device.mimeType}).arrayBuffer())}finally{await audio.close()}
     if(decoded.duration>61)throw Error();const target=new OfflineAudioContext(1,Math.min(60*24000,Math.ceil(decoded.duration*24000)),24000);const source=target.createBufferSource();source.buffer=decoded;source.connect(target.destination);source.start();const rendered=await target.startRendering();setFile(wav(rendered.getChannelData(0)));setKind("voice");
    }catch{setError("Could not prepare the recording. Upload a mono 16-bit WAV at 16/24 kHz instead.")}};
   device.start();setRecording(true);timer.current=setTimeout(()=>{if(device.state==="recording")device.stop()},60000);
  }catch{setError("Microphone access is unavailable. You can upload a WAV or type your goal.")}
 }
 async function save(){
  setBusy(true);setError("");
  try{const body=new FormData();body.set("workspace_id",workspace);body.set("generation_mode",mode);body.set("kind",kind);body.set("notes",notes);body.set("consent",String(consent));if(file)body.set("file",file);
   const response=await fetch(BASE+"/api/v1/business-context",{method:"POST",headers:{Authorization:"Bearer "+token},body});const data=await response.json();if(!response.ok)throw Error(typeof data.detail==="string"?data.detail:"Context processing failed");
   setRows(old=>[data,...old.filter(item=>item.id!==data.id)]);if(kind==="voice")setVoice(data.text.slice(0,600));
   const ids=[...selected.filter(id=>id!==data.id),data.id].slice(-3);setSelected(ids);onSelect(ids);
  }catch(error){setError(error instanceof Error?error.message:"Context processing failed")}
  finally{setBusy(false)}
 }
 return <details className="product-card" open><summary>Visual Business Twin & Voice-to-Action</summary><p className="section-description">Reuse product, store, document and operations context across your mission. Model interpretation stays separate from verified facts. Saved context uses no credits.</p>
  {error&&<p role="alert" className="inline-warning">{error}</p>}
  <div className="field-grid"><label>Context type<select aria-label="Context type" value={kind} onChange={event=>setKind(event.target.value)}><option value="business_twin">Business twin · photo, document, video or notes</option><option value="voice">Voice goal · WAV recording</option></select></label><label>Context file<input aria-label="Business context file" type="file" accept={kind==="voice"?"audio/wav,audio/x-wav":"image/png,image/jpeg,image/webp,application/pdf,video/mp4"} onChange={event=>setFile(event.target.files?.[0]||null)}/></label></div>
  <label>Business operations context<textarea aria-label="Business operations context" rows={2} maxLength={1800} value={notes} onChange={event=>setNotes(event.target.value)} placeholder="Your products, customers, constraints or operational details"/></label>
  <div className="button-row"><button type="button" className="secondary" disabled={busy} onClick={capture}>{recording?"Stop recording":"Record a voice goal"}</button><span className="field-help">{file?file.name:"Optional file. Notes alone use no model call."}</span></div>
  <label className="checkbox-label"><input type="checkbox" checked={consent} onChange={event=>setConsent(event.target.checked)}/>I can share this context with the model. Voice input is a draft, never execution approval.</label>
  <button type="button" className="secondary" disabled={busy||recording||!consent||(!file&&notes.trim().length<10)} onClick={save}>{busy?"Understanding your business…":kind==="voice"?"Transcribe voice goal":"Save business context"}</button>
  <p className="field-help">Each live file review or transcription uses one budgeted request. WAV: up to 60 seconds; images/PDF/MP4: up to 5 MB. PDF/MP4 and voice are account-verified only after a successful live request. No segmentation or generated video is claimed.</p>
  {voice&&<div><label>Review the voice goal<textarea aria-label="Reviewed voice goal" maxLength={600} rows={3} value={voice} onChange={event=>setVoice(event.target.value)}/></label><button type="button" className="primary" disabled={voice.length<10} onClick={()=>onGoal(voice)}>Use reviewed voice goal</button><p className="field-help">This only fills the goal. You still choose when to start the mission.</p></div>}
  {rows.map(item=><article className="finding" key={item.id}><label className="checkbox-label"><input type="checkbox" disabled={item.status!=="completed"} checked={selected.includes(item.id)} onChange={()=>choose(item.id)}/>Use {item.filename} in this mission</label><SourceBadge value={item.provenance}/><details><summary>Inspect saved context</summary><p className="field-help">{item.limitation}</p><pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{item.text}</pre></details></article>)}
 </details>;
}
