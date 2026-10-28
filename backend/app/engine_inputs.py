"""Bounded audio and public citation parsing. No network or inference here."""
import io
import ipaddress
import wave
from urllib.parse import urlsplit


def public_link(value):
    try:
        parsed=urlsplit(value)
        host=(parsed.hostname or "").lower()
        if parsed.scheme!="https" or not host or parsed.username or parsed.password or parsed.port not in (None,443):return False
        if host=="localhost" or host.endswith((".local",".internal")) or "." not in host:return False
        try:return ipaddress.ip_address(host).is_global
        except ValueError:return True
    except (ValueError,TypeError):return False


def wav_duration(payload,mime):
    if mime not in ("audio/wav","audio/x-wav") or not isinstance(payload,bytes) or not 44<=len(payload)<=3_000_000:
        raise ValueError("Use a mono 16-bit PCM WAV recording, up to 60 seconds")
    try:
        with wave.open(io.BytesIO(payload),"rb") as clip:
            frames=clip.getnframes();rate=clip.getframerate()
            if clip.getnchannels()!=1 or clip.getsampwidth()!=2 or rate not in (16000,24000) or clip.getcomptype()!="NONE":raise ValueError()
            duration=round(frames*1000/rate)
            if not 1<=duration<=60000 or len(clip.readframes(frames))!=frames*2:raise ValueError()
            return duration
    except Exception:raise ValueError("Use a complete mono 16-bit PCM WAV at 16/24 kHz, up to 60 seconds") from None


def grounded_response(response):
    if response.get("status")!="completed":raise ValueError("Search response incomplete")
    searches=[item for item in response.get("output",[]) if item.get("type")=="web_search_call" and item.get("status")=="completed"]
    if len(searches)!=1:raise ValueError("Exactly one completed search is required")
    text="";citations=[];hits=[]
    for item in response.get("output",[]):
        if item.get("type")!="message":continue
        for block in item.get("content",[]):
            if block.get("type")!="output_text":continue
            value=block.get("text","");offset=len(text)
            if not isinstance(value,str):raise ValueError("Invalid search text")
            for citation in block.get("annotations",[]):
                start=citation.get("start_index");end=citation.get("end_index")
                if citation.get("type")!="url_citation" or not public_link(citation.get("url")):continue
                if not isinstance(start,int) or not isinstance(end,int) or not 0<=start<end<=len(value):continue
                citations.append({"url":citation["url"],"title":str(citation.get("title","Source"))[:200],
                    "start_index":start+offset,"end_index":end+offset})
            text+=value
    if not text.strip() or len(text)>12000 or not citations:raise ValueError("Search must return bounded text with valid URL citations")
    for item in (searches[0].get("results") or [])[:10]:
        if item.get("type")=="text_result" and public_link(item.get("url")):
            hits.append({"url":item["url"],"title":str(item.get("title","Source"))[:200],"snippet":str(item.get("snippet",""))[:1000]})
    return {"summary":text,"citations":citations[:20],"results":hits,"searched":True,
        "limitation":"Provider search citations are evidence pointers, not independent verification of business claims."}
