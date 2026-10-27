import {NextRequest} from "next/server";

export const dynamic="force-dynamic";

async function forward(request:NextRequest,context:{params:Promise<{path:string[]}>}){
 const {path}=await context.params;
 if(path.length<1||path.length>2||!/^[A-Za-z0-9_-]{10,80}$/.test(path[0])||(path.length===2&&path[1]!=="lead"))return new Response("Not found",{status:404});
 if(request.method==="POST"&&(path.length!==2||Number(request.headers.get("content-length")||0)>8192))return new Response("Invalid inquiry",{status:400});
 const upstream=process.env.INTERNAL_API_URL||"http://127.0.0.1:8000";
 try{
   const body=request.method==="POST"?await request.text():undefined;
   if(body&&body.length>8192)return new Response("Inquiry too large",{status:413});
   const result=await fetch(upstream+"/p/"+path.map(encodeURIComponent).join("/"),{
     method:request.method,headers:body?{"Content-Type":"application/x-www-form-urlencoded"}:{},body,cache:"no-store",redirect:"manual",signal:AbortSignal.timeout(15000)});
   const headers=new Headers();
   for(const name of ["content-type","content-security-policy","x-content-type-options","referrer-policy","cache-control"]){const value=result.headers.get(name);if(value)headers.set(name,value)}
   headers.set("Cache-Control","no-store");
   return new Response(result.body,{status:result.status,headers});
 }catch{return new Response("Page temporarily unavailable",{status:503})}
}
export const GET=forward;
export const POST=forward;
