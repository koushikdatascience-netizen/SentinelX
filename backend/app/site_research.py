"""Deterministic, bounded public discovery. All transport stays DNS pinned."""
import hashlib
import json
import re
import time
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit,urlunsplit
from urllib.robotparser import RobotFileParser
from defusedxml.ElementTree import fromstring
from app.public_web import request_public,inspect_html
from app.engine_inputs import public_link

AGENT="SentinelX"
PLATFORMS={"facebook.com":"Facebook","instagram.com":"Instagram","youtube.com":"YouTube",
    "youtu.be":"YouTube","linkedin.com":"LinkedIn","x.com":"X","twitter.com":"X","pinterest.com":"Pinterest"}


def canonical_url(url,base=None):
    url=urljoin(base,url) if base else url
    try:parts=urlsplit(url)
    except ValueError:return None
    if not public_link(url) or parts.port not in (None,443) or len(url)>2000:return None
    # Query URLs are not recursively traversed: avoid carts, search and tracking loops.
    if parts.query:return None
    return urlunsplit(("https",parts.hostname.lower(),parts.path or "/","",""))


class DiscoveryHTML(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.description="";self.robots="";self.canonical="";self.headings=[]
        self.schema=[];self.schema_text="";self.in_schema=False;self.claims=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=="a" and attrs.get("href") and len(self.links)<150:self.links.append(attrs["href"][:2000])
        if tag=="meta":
            name=(attrs.get("name") or "").lower()
            if name=="description":self.description=(attrs.get("content") or "")[:600]
            if name=="robots":self.robots=(attrs.get("content") or "")[:300]
        if tag=="link" and "canonical" in (attrs.get("rel") or "").split():self.canonical=(attrs.get("href") or "")[:2000]
        if re.fullmatch("h[1-6]",tag):self.headings.append(int(tag[1]))
        if tag=="script" and attrs.get("type")=="application/ld+json":self.in_schema=True;self.schema_text=""
    def handle_data(self,data):
        if self.in_schema:self.schema_text=(self.schema_text+data)[:20000]
    def handle_endtag(self,tag):
        if tag=="script" and self.in_schema:
            try:
                value=json.loads(self.schema_text)
                self.schema.append({"valid_json":True,"types":_schema_types(value)})
                queue=[value];visited=0
                while queue and visited<40:
                    item=queue.pop(0);visited+=1
                    if isinstance(item,list):queue.extend(item[:20]);continue
                    if not isinstance(item,dict):continue
                    for key in ("name","description","address","openingHours","areaServed","price","priceCurrency","telephone","email","logo"):
                        if key in item and len(self.claims)<40:
                            encoded=json.dumps(item[key],ensure_ascii=False)
                            if len(encoded)<=1500:self.claims.append({"kind":key,"value":item[key],"schema_type":str(item.get("@type",""))[:80]})
                    for key in ("@graph","offers","brand","department"): 
                        if key in item:queue.append(item[key])
                    same_as=item.get("sameAs",[])
                    if isinstance(same_as,str):same_as=[same_as]
                    if isinstance(same_as,list):self.links.extend(link[:2000] for link in same_as[:10] if isinstance(link,str))
            except (ValueError,RecursionError):self.schema.append({"valid_json":False,"types":[]})
            self.in_schema=False


def _schema_types(value):
    if isinstance(value,dict):
        entries=value.get("@graph",[value])
        return [str(item.get("@type",""))[:100] for item in entries[:20] if isinstance(item,dict)] if isinstance(entries,list) else []
    if isinstance(value,list):return [str(item.get("@type",""))[:100] for item in value[:20] if isinstance(item,dict)]
    return []


def analyze_page(raw,role):
    html=raw["html"];parser=DiscoveryHTML();parser.feed(html);parsed=inspect_html(html)
    page={key:value for key,value in raw.items() if key!="html"}
    page.update(parsed);page.update(role=role,origin="retrieved_public_page",description=parser.description,robots=parser.robots,
        canonical=parser.canonical,headings=parser.headings[:100],structured_data=parser.schema[:10],structured_claims=parser.claims)
    page["id"]="page-"+hashlib.sha256(page["url"].encode()).hexdigest()[:16]
    page["links"]=list(dict.fromkeys(filter(None,(canonical_url(link,page["url"]) for link in parser.links))))[:100]
    page["contacts"]={"phones":list(dict.fromkeys(link[4:] for link in parser.links if link.lower().startswith("tel:")))[:10],
        "emails":list(dict.fromkeys(link[7:].split("?",1)[0] for link in parser.links if link.lower().startswith("mailto:")))[:10]}
    page["profiles"]=[]
    for link in page["links"]:
        host=urlsplit(link).hostname.removeprefix("www.")
        platform=PLATFORMS.get(host)
        if platform and urlsplit(link).path not in ("/",""):
            page["profiles"].append({"url":link,"platform":platform,"verification":"website_linked_candidate",
                "evidence_id":page["id"],"source_url":page["url"],"identity_confirmed":False})
    return page


def findings(page):
    signals=page["signals"];checks=[]
    for condition,title,why,action in [
        (not page["title"],"Missing page title","Search results and browser tabs lack a descriptive title.","Add a unique descriptive title."),
        (not page["description"],"Missing meta description","No description metadata was observed in static HTML.","Write a factual page-specific description."),
        (not signals["viewport"],"No viewport metadata","Mobile layout intent is not declared in static HTML.","Review the responsive layout and add viewport metadata."),
        (signals["h1_count"]!=1,"Review main heading","Static HTML has "+str(signals["h1_count"])+" h1 elements.","Review heading hierarchy and use one clear main heading."),
        (signals["images_without_alt"]>0,"Images missing descriptions",str(signals["images_without_alt"])+" images lack nonempty alt text; decorative images need contextual review.","Add descriptive alt text where images convey meaning."),
        ("noindex" in page["robots"].lower(),"Page declares noindex","Indexing is explicitly discouraged by page metadata.","Confirm whether excluding this page from search is intentional."),
        (not any(signals[k] for k in ("forms","phone_links","email_links","whatsapp_links")),"No measured inquiry path","No HTML form, telephone, email or WhatsApp link was counted.","Review the actual customer inquiry journey before adding a CTA."),
        (any(not schema["valid_json"] for schema in page["structured_data"]),"Invalid JSON-LD","A structured-data block is not valid JSON.","Repair the JSON syntax and validate its schema separately.")]:
        if condition:checks.append({"finding":title,"evidence_id":page["id"],"source":page["url"],
            "confidence":"observed_static_html","why":why,"recommended_action":action,"effort":"owner review required",
            "potential_impact":"Hypothesis; no conversion or ranking uplift measured","requires_approval":True,
            "execution_eligible":False,"dependencies":["Owner review","Authorized website deployment"]})
    return checks


def sitemap_urls(text,origin):
    root=fromstring(text)
    return list(dict.fromkeys(url for node in root.iter() if node.tag.rsplit("}",1)[-1]=="loc"
        and (url:=canonical_url((node.text or "").strip())) and urlsplit(url).hostname==origin))[:100]


def crawl(state,checkpoint,cancelled,pause=time.sleep):
    """One request at a time, persisted checkpoints; no LLM or browser navigation."""
    started=time.monotonic();policies={};last_request={};state.setdefault("requests",0)
    def fetch(url,types):
        if state["requests"]>=40 or time.monotonic()-started>300:raise TimeoutError("Research request/time limit reached")
        host=urlsplit(url).hostname
        delay=policies.get(host,{}).get("delay",1)
        wait=delay-(time.monotonic()-last_request.get(host,0))
        if wait>0:pause(wait)
        if cancelled():raise InterruptedError("Cancellation requested")
        state["requests"]+=1;last_request[host]=time.monotonic()
        # Persist the attempt before transport so restart/resume cannot reset it.
        checkpoint(state)
        parser=policies.get(host,{}).get("parser")
        return request_public(url,content_types=types,same_host=host,
            allow_url=(lambda target:parser.can_fetch(AGENT,target)) if parser else None)
    while state["queue"] and len(state["pages"])<state["max_pages"]:
        if cancelled():return "cancelled"
        url,depth,role=state["queue"][0];host=urlsplit(url).hostname
        if url in state["visited"]:state["queue"].pop(0);continue
        try:
            if host not in policies:
                robots=fetch("https://"+host+"/robots.txt",("text/plain","text/html"))
                rp=RobotFileParser()
                if robots["status"]==404:rp.parse([])
                elif robots["status"]==200:rp.parse(robots["html"].splitlines())
                else:raise ValueError("robots.txt unavailable or access denied")
                delay=max(1,rp.crawl_delay(AGENT) or rp.crawl_delay("*") or 1)
                rate=rp.request_rate(AGENT) or rp.request_rate("*")
                if rate:delay=max(delay,rate.seconds/max(rate.requests,1))
                if delay>30:raise ValueError("Requested crawl rate exceeds this bounded job's time window")
                policies[host]={"parser":rp,"delay":delay}
                state.setdefault("coverage",[]).append({"host":host,"robots_status":robots["status"],"collected_at":robots["collected_at"]})
                maps=rp.site_maps() or ["https://"+host+"/sitemap.xml"]
                for candidate in maps[:1]:
                    candidate=canonical_url(candidate)
                    if candidate and urlsplit(candidate).hostname==host and rp.can_fetch(AGENT,candidate):
                        try:
                            response=fetch(candidate,("application/xml","text/xml","text/plain"))
                            if response["status"]==200:
                                discovered=sitemap_urls(response["html"],host)[:30]
                                nested=next((link for link in discovered if link.lower().endswith(".xml") and rp.can_fetch(AGENT,link)),None)
                                if nested:
                                    child=fetch(nested,("application/xml","text/xml","text/plain"))
                                    if child["status"]==200:discovered+=sitemap_urls(child["html"],host)[:30]
                                for link in discovered:
                                    if not link.lower().endswith(".xml"):state["queue"].append([link,1,role])
                        except (ValueError,OSError):state.setdefault("limitations",[]).append("Sitemap unavailable for "+host)
            if not policies[host]["parser"].can_fetch(AGENT,url):
                state["errors"].append({"url":url,"reason":"robots.txt disallows this path"})
            else:
                response=fetch(url,("text/html",))
                if response["status"]!=200:raise ValueError("HTTP "+str(response["status"]))
                page=analyze_page(response,role);state["pages"].append(page)
                if depth<state["max_depth"]:
                    links=[link for link in page["links"] if urlsplit(link).hostname==host]
                    links.sort(key=lambda link:0 if re.search(r"about|product|service|contact|faq|pricing|location",link,re.I) else 1)
                    state["queue"].extend([link,depth+1,role] for link in links[:30] if link not in state["visited"])
        except InterruptedError:return "cancelled"
        except TimeoutError:
            state["limitations"].append("Time/request budget reached; resume explicitly from this checkpoint.")
            checkpoint(state);return "paused"
        except Exception as exc:
            state["errors"].append({"url":url,"reason":str(exc)[:160] if isinstance(exc,ValueError) else type(exc).__name__})
            if host not in policies:
                # An unavailable robots policy blocks every page on this host.
                state["queue"]=[entry for entry in state["queue"] if urlsplit(entry[0]).hostname!=host]
        state["visited"].append(url)
        state["queue"]=[entry for entry in state["queue"] if entry[0] not in state["visited"]][:150]
        checkpoint(state)
        if len(state["visited"])>=30:
            state["limitations"].append("Visited-URL limit reached; remaining URLs were not inspected.")
            break
    return "completed" if state["pages"] else "failed"
