"use client";
import {useState} from "react";
const BASE=process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type Workspace={id:string;name:string};
export default function Home(){
 const [email,setEmail]=useState("");const [password,setPassword]=useState("");
 const [token,setToken]=useState("");const [workspaces,setWorkspaces]=useState<Workspace[]>([]);
 const [workspaceName,setWorkspaceName]=useState("My Business");const [active,setActive]=useState("");
 const [useInference,setUseInference]=useState(false);const [website,setWebsite]=useState("https://example.com");const [goal,setGoal]=useState("Improve customer conversion from my website");
 const [output,setOutput]=useState<unknown>(null);const [error,setError]=useState("");const [busy,setBusy]=useState(false);
 async function call(path:string,method="GET",body?:unknown,auth=token){
  setError("");setBusy(true);
  try {
   const res=await fetch(BASE+path,{method,headers:{"Content-Type":"application/json",...(auth?{Authorization:"Bearer "+auth}:{})},body:body?JSON.stringify(body):undefined});
   const data=await res.json();if(!res.ok)throw Error(typeof data.detail==="string"?data.detail:"Request failed");
   setOutput(data);return data;
  }catch(e){setError(e instanceof Error?e.message:"Request failed");return null}finally{setBusy(false)}
 }
 async function authenticate(kind:"register"|"login"){
  const data=await call("/api/v1/auth/"+kind,"POST",{email,password},"");
  if(kind==="login"&&data?.access_token){setToken(data.access_token); const list=await call("/api/v1/workspaces","GET",undefined,data.access_token);if(Array.isArray(list))setWorkspaces(list)}
 }
 async function createWorkspace(){const w=await call("/api/v1/workspaces","POST",{name:workspaceName});if(w?.id){setActive(w.id);setWorkspaces([...workspaces,w])}}
 return <main><p className="tag">SENTINELX / HACKATHON 2026</p><h1>Business Intelligence Command Center</h1><p className="muted">Evidence-first research · Human-approved actions · Multimodal AI foundation</p>
 <div className="columns"><section className="card"><h2>1. Account</h2><label>Email<input type="email" value={email} onChange={e=>setEmail(e.target.value)}/></label><label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)}/></label><button disabled={busy} onClick={()=>authenticate("register")}>Register</button>{" "}<button disabled={busy} onClick={()=>authenticate("login")}>Sign in</button><p className="muted">Session token kept only in this browser tab's React memory.</p></section>
 <section className="card"><h2>2. Workspace</h2><label>Name<input value={workspaceName} onChange={e=>setWorkspaceName(e.target.value)}/></label><button disabled={!token||busy} onClick={createWorkspace}>Create workspace</button><p className="muted">Select a business workspace:</p><select aria-label="Workspace" value={active} onChange={e=>setActive(e.target.value)}><option value="">Select workspace</option>{workspaces.map(w=><option key={w.id} value={w.id}>{w.name}</option>)}</select></section></div>
 <section className="card"><h2>3. Start a business analysis</h2><label>Website<input value={website} onChange={e=>setWebsite(e.target.value)}/></label><label>Business goal<input value={goal} onChange={e=>setGoal(e.target.value)}/></label><label><input type="checkbox" checked={useInference} onChange={e=>setUseInference(e.target.checked)}/> Use configured inference provider (may have quotas or charges)</label><button disabled={!token||!active||busy} onClick={()=>call("/api/v1/workspaces/"+active+"/runs","POST",{website,goal,use_inference:useInference})}>Create workflow run</button><p className="muted">Stored in database. The seven-agent response is a clearly labeled simulated preview, not real Meta inference.</p></section>
 {error&&<section className="card" role="alert">Error: {error}</section>}
 {output!==null&&<section className="card"><h2>API result</h2><pre>{JSON.stringify(output,null,2)}</pre></section>}
 <p className="muted">Development dashboard only. Do not expose publicly until production authentication, CORS and abuse protections are configured.</p></main>;
}
