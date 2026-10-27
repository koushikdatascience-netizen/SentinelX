"use client";
import {useEffect,useRef} from "react";

export function ProductIcon({name,size=20}:{name:string;size?:number}){
 const paths:Record<string,string>={
  dashboard:"M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  campaign:"M4 5h16v16H4zM4 10h16M8 3v4M16 3v4M8 14h2M14 14h2M8 18h2",
  image:"M3 3h18v18H3zM3 17l5-5 4 4 3-3 6 6M16 7h.01",
  landing:"M3 3h18v18H3zM3 8h18M8 8v13",
  review:"M9 3h6v4H9zM9 5H5v16h14V5h-4M8 14l3 3 5-6",
  report:"M6 3h8l4 4v14H6zM14 3v5h4M9 12h6M9 16h6",
  settings:"M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2",
  arrow:"M5 12h14M14 7l5 5-5 5",back:"M19 12H5M10 7l-5 5 5 5",plus:"M12 5v14M5 12h14",
  close:"M6 6l12 12M6 18 18 6",check:"M5 12l4 4L19 6",download:"M12 3v12M7 10l5 5 5-5M4 16v5h16v-5",
  copy:"M9 9h12v12H9zM15 5V3H3v12h2",edit:"m16 3 5 5-12 12-6 1 1-6zM14 5l5 5",
  spark:"m12 3 2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3z",
  upload:"M12 16V3M7 8l5-5 5 5M4 16v5h16v-5",globe:"M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0M3 12h18M12 3c-5 5-5 13 0 18M12 3c5 5 5 13 0 18",
  logout:"M9 3H3v18h6M9 12h12M16 7l5 5-5 5",menu:"M4 6h16M4 12h16M4 18h16",
 };
 return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]||paths.spark}/></svg>;
}

export function SourceBadge({value}:{value:string}){
 return <span className={`source-badge ${value==="live_meta"?"source-live":value==="sample"?"source-sample":"source-owner"}`}><span/>{value==="live_meta"?"Meta AI generated":value==="sample"?"Sample content":"Your content"}</span>;
}

export function Modal({title,onClose,children,wide=false}:{title:string;onClose:()=>void;children:React.ReactNode;wide?:boolean}){
 const ref=useRef<HTMLDialogElement>(null);
 useEffect(()=>{const dialog=ref.current;dialog?.showModal();return()=>dialog?.close()},[]);
 return <dialog ref={ref} className={`product-modal ${wide?"modal-wide":""}`} aria-label={title} onCancel={event=>{event.preventDefault();onClose()}} onClick={event=>{if(event.target===event.currentTarget)onClose()}}>
  <div className="modal-header"><h2>{title}</h2><button className="icon-button" onClick={onClose} aria-label="Close dialog"><ProductIcon name="close"/></button></div>
  <div className="modal-body">{children}</div>
 </dialog>;
}

export function EmptyState({icon="campaign",title,children,action}:{icon?:string;title:string;children:React.ReactNode;action?:React.ReactNode}){
 return <div className="product-empty"><span className="empty-icon"><ProductIcon name={icon} size={28}/></span><h3>{title}</h3><p>{children}</p>{action}</div>;
}
