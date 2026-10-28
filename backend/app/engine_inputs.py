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


def context_excerpt(text,omit_quoted_intro=False):
    """Select bounded prior-output excerpts; keep the complete original for audit."""
    if omit_quoted_intro:
        lines=text.splitlines()
        while lines and (not lines[0].strip() or lines[0].lstrip().startswith(">")):
            lines.pop(0)
        text="\n".join(lines)
    text=text.strip()
    return text if len(text)<=520 else text[:390]+"\n[excerpt omitted]\n"+text[-110:]


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
    text="";citations=[];hits=[];annotation_seen=False
    for item in response.get("output",[]):
        if item.get("type")!="message":continue
        for block in item.get("content",[]):
            if block.get("type")!="output_text":continue
            value=block.get("text","")
            if not isinstance(value,str):raise ValueError("Invalid search text")
            if text:text+="\n\n"
            offset=len(text)
            for citation in block.get("annotations") or []:
                if citation.get("type")=="url_citation":annotation_seen=True
                start=citation.get("start_index");end=citation.get("end_index")
                if citation.get("type")!="url_citation" or not public_link(citation.get("url")):continue
                if not isinstance(start,int) or not isinstance(end,int) or not 0<=start<end<=len(value):continue
                citations.append({"url":citation["url"],"title":str(citation.get("title","Source"))[:200],
                    "start_index":start+offset,"end_index":end+offset})
            text+=value
    if not text.strip() or len(text)>12000:raise ValueError("Search must return bounded text")
    for item in (searches[0].get("results") or [])[:10]:
        if item.get("type")=="text_result" and public_link(item.get("url")):
            hits.append({"url":item["url"],"title":str(item.get("title","Source"))[:200],"snippet":str(item.get("snippet",""))[:1000]})
    if annotation_seen and not citations:raise ValueError("Invalid search citation annotations")
    inline=bool(citations)
    if not citations:
        if not hits:raise ValueError("Search returned neither valid annotations nor public source results")
        citations=[{"url":hit["url"],"title":hit["title"],"start_index":None,"end_index":None} for hit in hits]
    return {"summary":text,"citations":citations[:20],"results":hits,"searched":True,
        "citation_mode":"url_annotations" if inline else "provider_results","has_inline_citations":inline,
        "limitation":"Provider URL annotations are evidence pointers, not independent verification of business claims." if inline else
            "The provider returned search-result links without inline URL annotations. Summary claims are not span-cited. Only independently collected page text can support the mission's source-checked quotes."}
