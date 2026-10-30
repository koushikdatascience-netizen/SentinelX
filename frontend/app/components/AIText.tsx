"use client";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

function safeUrl(value:string){
 if(value.startsWith("#"))return value;
 try{const url=new URL(value);return ["https:","http:"].includes(url.protocol)&&!url.username&&!url.password?url.href:""}catch{return ""}
}

/** Presentation only: stored text, provenance, citations and exports stay unchanged. */
export default function AIText({text,compact=false}:{text?:string|null;compact?:boolean}){
 return <div className={`ai-prose ${compact?"ai-prose-compact":""}`}><Markdown remarkPlugins={[remarkGfm]} skipHtml urlTransform={safeUrl} components={{
  h1:({children})=><h3>{children}</h3>,h2:({children})=><h3>{children}</h3>,h3:({children})=><h4>{children}</h4>,
  a:({href,children})=>href?<a href={href} target={href.startsWith("#")?undefined:"_blank"} rel="noreferrer noopener">{children}</a>:<span>{children}</span>,
  img:({alt})=><span className="ai-image-reference">Image reference: {alt||"See the saved asset"}</span>,
  table:({children})=><div className="ai-table-scroll" role="region" aria-label="Report table" tabIndex={0}><table>{children}</table></div>,
 }}>{text||""}</Markdown></div>;
}
