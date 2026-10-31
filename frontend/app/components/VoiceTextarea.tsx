"use client";
import {useId,useRef,type TextareaHTMLAttributes} from "react";
import PromptVoiceInput from "./PromptVoiceInput";

type Props=Omit<TextareaHTMLAttributes<HTMLTextAreaElement>,"value"|"onChange">&{label:string;value:string;onChange:(value:string)=>void;token:string;workspace:string;available:boolean;onVoiceActivity?:(active:boolean)=>void};
export default function VoiceTextarea({label,value,onChange,token,workspace,available,onVoiceActivity,id,disabled,maxLength,...props}:Props){
 const generated=useId();const fieldId=id||generated;const current=useRef({value,onChange});current.current={value,onChange};
 return <div className="voice-field"><label htmlFor={fieldId}>{label}</label><div className="voice-field-input"><textarea {...props} id={fieldId} value={value} disabled={disabled} maxLength={maxLength} onChange={event=>onChange(event.target.value)}/><div className="voice-field-mic" title={available?"Record and transcribe into this field":"Voice input requires live Meta transcription"}><PromptVoiceInput compact token={token} workspace={workspace} available={available} disabled={disabled} onActivityChange={onVoiceActivity} onTranscript={text=>current.current.onChange([current.current.value.trimEnd(),text].filter(Boolean).join(" ").slice(0,maxLength||100000))}/></div></div></div>;
}
