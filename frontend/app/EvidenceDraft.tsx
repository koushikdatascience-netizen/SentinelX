"use client";

type Analysis = {
 recommendations: Array<{action:string;reason:string;source_id:string;quote:string;priority:string}>;
 assumptions: string[];
 artifact: {title:string;body:string};
};

export default function EvidenceDraft({result}:{result:Record<string,unknown>}) {
 const analysis=result.analysis as Analysis|undefined;
 const usage=result.usage as {prompt_tokens?:number;completion_tokens?:number;reasoning_tokens?:number}|undefined;
 const sources=result.evidence as Array<{id:string;source_url:string;excerpt:string}>|undefined;
 if(result.mode!=="model_evidence_draft")return null;
 return <section aria-label="Evidence draft result">
  <h3>Evidence → interpretation → draft</h3>
  <p className="muted">{String(result.provider)} · {String(result.model)} · Owner-supplied evidence is unverified.</p>
  {sources?.map(source=><details key={source.id}><summary>View supplied source {source.id}</summary><p>{source.source_url}</p><blockquote>{source.excerpt}</blockquote></details>)}
  {Boolean(result.error)&&<p role="alert">Generation failed. No automatic retry was made. Usage may have been consumed; inspect the saved run before trying a new request.</p>}
  {!analysis&&!result.error&&<p>Generation was claimed. Refresh run history to check its status; do not submit a new request while it is pending.</p>}
  {analysis&&<>
   {analysis.recommendations.map((item,i)=><article className="finding" key={i}>
    <small>AI interpretation · {item.priority} priority · human review required</small>
    <h4>{item.action}</h4><p>{item.reason}</p>
    <blockquote>{item.quote}</blockquote><small>Exact quote from {item.source_id}; quote presence does not establish claim accuracy.</small>
   </article>)}
   <h4>Assumptions and unknowns</h4>
   {analysis.assumptions.length?<ul>{analysis.assumptions.map((a,i)=><li key={i}>{a}</li>)}</ul>:<p>No assumptions listed by the model. Owner review is still required.</p>}
   <article className="panel"><small>GENERATED DRAFT · REQUIRES OWNER REVIEW</small><h3>{analysis.artifact.title}</h3>
    <p style={{whiteSpace:"pre-wrap"}}>{analysis.artifact.body}</p>
    <p className="muted">Included in the downloadable audit report. Nothing has been published externally.</p>
   </article>
  </>}
  {usage&&<p className="muted">Tokens: {usage.prompt_tokens??"unknown"} input · {usage.completion_tokens??"unknown"} output (including {usage.reasoning_tokens??"unknown"} reasoning). Actual charges require provider reconciliation.</p>}
 </section>;
}
