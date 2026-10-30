"use client";
import { useEffect, useRef, useState, useId } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

function pcmWav(samples: Float32Array) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const text = (offset: number, value: string) => [...value].forEach((char, index) => view.setUint8(offset + index, char.charCodeAt(0)));
  text(0, "RIFF"); view.setUint32(4, 36 + samples.length * 2, true); text(8, "WAVE");
  text(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, 1, true); view.setUint32(24, 24000, true); view.setUint32(28, 48000, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true); text(36, "data");
  view.setUint32(40, samples.length * 2, true);
  samples.forEach((sample, index) => { const value = Math.max(-1, Math.min(1, sample)); view.setInt16(44 + index * 2, value < 0 ? value * 32768 : value * 32767, true); });
  return new File([buffer], "prompt-dictation.wav", { type: "audio/wav" });
}

export default function PromptVoiceInput({token,workspace,available,disabled=false,compact=false,onTranscript,onActivityChange}:{
  token:string;workspace:string;available:boolean;disabled?:boolean;compact?:boolean;onTranscript:(value:string)=>void;onActivityChange?:(active:boolean)=>void;
}) {
  const [recording,setRecording]=useState(false);const [busy,setBusy]=useState(false);const [starting,setStarting]=useState(false);const [error,setError]=useState("");
  const recorder=useRef<MediaRecorder|null>(null);const stream=useRef<MediaStream|null>(null);
  const timer=useRef<ReturnType<typeof setTimeout>|null>(null);const mounted=useRef(true);const abort=useRef<AbortController|null>(null);
  const activity=useRef(onActivityChange);activity.current=onActivityChange;const hint=useId();
  useEffect(()=>{activity.current?.(recording||busy||starting)},[recording,busy,starting]);
  useEffect(()=>{mounted.current=true;return()=>{
    mounted.current=false;if(timer.current)clearTimeout(timer.current);abort.current?.abort();
    if(recorder.current?.state==="recording")recorder.current.stop();
    stream.current?.getTracks().forEach(track=>track.stop());activity.current?.(false);
  }},[]);
  async function transcribe(chunks:BlobPart[],mime:string,requestId:string){
    if(!mounted.current)return;setBusy(true);setError("");
    try{
      const context=new AudioContext();let decoded:AudioBuffer;
      try{decoded=await context.decodeAudioData(await new Blob(chunks,{type:mime}).arrayBuffer())}finally{await context.close()}
      if(decoded.duration<0.5||decoded.duration>60.5)throw Error("Record between half a second and 60 seconds.");
      const target=new OfflineAudioContext(1,Math.min(1440000,Math.ceil(decoded.duration*24000)),24000);
      const source=target.createBufferSource();source.buffer=decoded;source.connect(target.destination);source.start();
      const rendered=await target.startRendering();if(!mounted.current)return;
      const form=new FormData();form.append("workspace_id",workspace);form.append("consent","true");form.append("request_id",requestId);
      form.append("file",pcmWav(rendered.getChannelData(0)));abort.current=new AbortController();
      const response=await fetch(BASE+"/api/v1/prompts/transcribe",{method:"POST",headers:{Authorization:"Bearer "+token},body:form,signal:abort.current.signal});
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw Error(typeof data.detail==="string"?data.detail:"Voice transcription failed.");
      if(data.provenance!=="live_meta"||typeof data.transcript!=="string"||!data.transcript.trim())throw Error("No live transcript returned. Please try a new recording.");
      if(mounted.current)onTranscript(data.transcript.trim());
    }catch(reason){if(mounted.current)setError(reason instanceof Error?reason.message:"Could not transcribe this recording.")}
    finally{if(mounted.current)setBusy(false)}
  }
  async function begin(){
    if(!available||disabled||busy||starting||recording)return;setStarting(true);setError("");
    try{
      if(!navigator.mediaDevices?.getUserMedia||typeof MediaRecorder==="undefined")throw Error("Voice recording needs a supported browser over HTTPS. You can still type your prompt.");
      const input=await navigator.mediaDevices.getUserMedia({audio:true});
      if(!mounted.current){input.getTracks().forEach(track=>track.stop());return}
      stream.current=input;const chunks:BlobPart[]=[];const device=new MediaRecorder(input);recorder.current=device;let interrupted=false;
      const requestId=crypto.randomUUID();
      device.ondataavailable=event=>{if(event.data.size)chunks.push(event.data)};
      device.onerror=()=>{interrupted=true;input.getTracks().forEach(track=>track.stop());if(mounted.current){setRecording(false);setError("Recording was interrupted; no audio was sent. Record again or type your prompt.")}};
      device.onstop=()=>{
        input.getTracks().forEach(track=>track.stop());stream.current=null;if(timer.current)clearTimeout(timer.current);
        if(mounted.current)setRecording(false);if(!interrupted)void transcribe(chunks,device.mimeType||"audio/webm",requestId);
      };
      device.start();setRecording(true);
      timer.current=setTimeout(()=>{if(device.state==="recording")device.stop()},59000);
    }catch(reason){
      stream.current?.getTracks().forEach(track=>track.stop());stream.current=null;
      if(mounted.current)setError(reason instanceof DOMException&&reason.name==="NotAllowedError"?"Microphone access was denied. Allow microphone access in your browser’s site permissions, then click the mic again.":reason instanceof Error?reason.message:"Microphone unavailable. Check browser permission or type your prompt.");
    }finally{if(mounted.current)setStarting(false)}
  }
  const label=recording?"Stop and transcribe voice prompt":busy?"Transcribing voice prompt":starting?"Waiting for microphone permission":"Record voice prompt";
  return <div className={`prompt-voice ${compact?"prompt-voice-compact":""}`}>
    <button type="button" className={recording?"secondary prompt-voice-stop":"secondary prompt-voice-button"} aria-label={label} aria-describedby={hint} aria-pressed={recording}
      title={recording?"Stop and send recording to Meta":"Record voice prompt; stopping sends audio to Meta"} disabled={disabled||busy||starting||!available} onClick={()=>recording?recorder.current?.stop():void begin()}>
      {busy||starting?<span className="research-spinner"/>:recording?<span className="voice-recording-dot"/>:<svg aria-hidden="true" viewBox="0 0 20 20" width="18" height="18"><rect x="7" y="2" width="6" height="11" rx="3"/><path d="M4.5 9.5a5.5 5.5 0 0 0 11 0M10 15v3m-3 0h6"/></svg>}
      {!compact&&<span>{recording?"Stop & transcribe":busy?"Transcribing…":starting?"Allow microphone…":"Voice input"}</span>}
    </button><span id={hint} className={compact?"sr-only":"field-help"}>Click the mic to allow microphone access. Stopping sends up to 60 seconds of audio to Meta. Review the inserted text before submitting; audio is not saved.</span>
    {!available&&!compact&&<p className="field-help">Voice dictation needs live Meta inference enabled. You can type your prompt.</p>}
    {error&&<p className="inline-warning" role="alert">{error}</p>}
  </div>;
}
