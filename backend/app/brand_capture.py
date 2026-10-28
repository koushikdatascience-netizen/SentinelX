"""Robots-aware, pinned public retrieval and browser rendering with no direct browser egress."""
import hashlib
import socket
import time
from html.parser import HTMLParser
from threading import Timer
from urllib.parse import urlsplit,urljoin,urlunsplit
from urllib.robotparser import RobotFileParser
from app.public_web import resolve_target,PinnedHTTPS,inspect_html

AGENT="SentinelXResearch"
RESTRICTED=("facebook.com","fb.com","fb.watch","instagram.com","threads.net","threads.com","youtube.com","youtu.be",
    "linkedin.com","tiktok.com","twitter.com","x.com","google.com","google.co.in","goo.gl","maps.app.goo.gl")
MAX_PAGES=10


def restricted(url):
    host=(urlsplit(url).hostname or "").lower().rstrip(".")
    return any(host==domain or host.endswith("."+domain) for domain in RESTRICTED)


def clean_url(url):
    p=urlsplit(url)
    if p.scheme!="https" or not p.hostname or p.username or p.password or p.port not in (None,443):
        raise ValueError("Use a public HTTPS URL without credentials")
    if len(url)>2000:raise ValueError("URL is too long")
    return urlunsplit((p.scheme,p.netloc.lower(),p.path or "/",p.query,""))


def fetch_bytes(url,maximum=2_000_000,authorize=None):
    """Each hop is checked and connected to the resolved public IP; no proxy or cookie jar."""
    for hop in range(3):
        if restricted(url):raise ValueError("Platform requires an approved API; direct scraping is disabled")
        if authorize and not authorize(url):raise ValueError("Redirect or resource access is disallowed")
        host,family,address,normalized=resolve_target(url)
        parsed=urlsplit(normalized)
        connection=PinnedHTTPS(host,family,address)
        def abort():
            if connection.sock:
                try:connection.sock.shutdown(socket.SHUT_RDWR)
                except OSError:pass
                connection.sock.close()
        timer=Timer(12,abort);timer.daemon=True;timer.start()
        try:
            connection.request("GET",parsed.path+("?"+parsed.query if parsed.query else ""),headers={
                "Host":host,"User-Agent":AGENT+"/1.0 owner-authorized brand review","Accept-Encoding":"identity"})
            response=connection.getresponse()
            if response.status in (301,302,303,307,308):
                destination=response.getheader("Location")
                if not destination or hop==2:raise ValueError("Redirect limit reached")
                url=urljoin(normalized,destination);continue
            if response.getheader("Content-Encoding","identity").lower() not in ("identity",""):
                raise ValueError("Unsupported response encoding")
            content=bytearray();deadline=time.monotonic()+10
            while True:
                if time.monotonic()>deadline:raise ValueError("Retrieval time limit reached")
                part=response.read1(min(16384,maximum+1-len(content)))
                if not part:break
                content.extend(part)
                if len(content)>maximum:raise ValueError("Resource exceeds byte limit")
            return {"url":normalized,"status":response.status,"mime":response.getheader("Content-Type","").split(";")[0].lower(),"content":bytes(content)}
        finally:timer.cancel();connection.close()
    raise ValueError("Redirect limit reached")


class SiteAccess:
    def __init__(self):
        self.robots={};self.cache={};self.bytes=0;self.requests=0;self.deadline=time.monotonic()+600

    def permitted(self,url):
        url=clean_url(url)
        if restricted(url):return False
        p=urlsplit(url);origin=p.scheme+"://"+p.netloc
        if origin not in self.robots:
            try:
                raw=fetch_bytes(origin+"/robots.txt",128_000)
                # 404 means no published rules; other errors fail closed.
                if raw["status"]==404:self.robots[origin]=None
                elif raw["status"]==200:
                    parser=RobotFileParser();parser.parse(raw["content"].decode("utf-8",errors="replace").splitlines());self.robots[origin]=parser
                else:self.robots[origin]=False
            except Exception:self.robots[origin]=False
        rules=self.robots[origin]
        return rules is None or (rules is not False and rules.can_fetch(AGENT,url))

    def get(self,url):
        url=clean_url(url)
        if url in self.cache:return self.cache[url]
        if self.requests>=160 or self.bytes>=25_000_000 or time.monotonic()>self.deadline:
            raise ValueError("Research network or time limit reached")
        if not self.permitted(url):raise ValueError("Access restricted by platform policy or robots.txt")
        self.requests+=1
        raw=fetch_bytes(url,authorize=self.permitted)
        if raw["url"]!=url and not self.permitted(raw["url"]):raise ValueError("Redirect destination disallows collection")
        if raw["status"]!=200:raise ValueError("Resource unavailable (HTTP "+str(raw["status"])+")")
        self.bytes+=len(raw["content"]);self.cache[url]=raw
        return raw


class PageInventory(HTMLParser):
    def __init__(self,base):
        super().__init__();self.base=base;self.links=[];self.images=[];self.contacts=[];self.description="";self.colors=[]

    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="a" and a.get("href"):
            href=a["href"]
            if href.startswith(("mailto:","tel:")):self.contacts.append(href[:200])
            elif len(self.links)<100:self.links.append(urljoin(self.base,href))
        if tag=="img" and (a.get("src") or a.get("data-src")) and len(self.images)<30:
            label=(a.get("alt","")+" "+a.get("class","")+" "+a.get("id","")).strip()[:250]
            self.images.append({"url":urljoin(self.base,a.get("src") or a["data-src"]),"alt":label,"kind":"logo" if "logo" in label.lower() else "image"})
        if tag=="link" and "icon" in a.get("rel","").lower() and a.get("href"):
            self.images.append({"url":urljoin(self.base,a["href"]),"alt":"Website icon","kind":"logo"})
        if tag=="meta" and a.get("name","").lower()=="description":self.description=a.get("content","")[:1000]


def page_details(raw):
    html=raw["content"].decode("utf-8",errors="replace")
    inventory=PageInventory(raw["url"]);inventory.feed(html)
    return {**inspect_html(html),"description":inventory.description,"links":inventory.links,
        "images":inventory.images,"contacts":list(dict.fromkeys(inventory.contacts)),
        "sha256":hashlib.sha256(raw["content"]).hexdigest(),"url":raw["url"]}


def candidate_pages(urls,website):
    host=(urlsplit(website).hostname or "").removeprefix("www.")
    candidates=[]
    for url in urls:
        try:url=clean_url(url)
        except ValueError:continue
        p=urlsplit(url)
        if (p.hostname or "").removeprefix("www.")!=host or p.query:continue
        if any(piece in p.path.lower() for piece in ("login","account","cart","checkout","logout","wp-admin")):continue
        if p.path.lower().endswith((".pdf",".zip",".jpg",".png",".webp",".mp4")):continue
        if url not in candidates:candidates.append(url)
    priority=lambda url:0 if any(word in url.lower() for word in ("product","service","about","contact","shop","collection")) else 1
    return sorted(candidates,key=priority)


def screenshots(raw,access):
    """Render retrieved public HTML with JS disabled; fulfill all network requests through pinned retrieval.

    Browser itself is offline. No credentials, service workers, scripts, video,
    arbitrary navigation or private network connections are permitted.
    """
    from playwright.sync_api import sync_playwright
    html=raw["content"].decode("utf-8",errors="replace")
    result=[]
    with sync_playwright() as runtime:
        browser=runtime.chromium.launch(headless=True,args=["--disable-dev-shm-usage"])
        try:
            context=browser.new_context(java_script_enabled=False,offline=True,service_workers="block",accept_downloads=False)
            def fulfill(route):
                request=route.request
                try:
                    if request.method!="GET" or request.resource_type not in ("document","image","stylesheet","font"):return route.abort()
                    if request.resource_type=="document":
                        if request.url.rstrip("/")!=raw["url"].rstrip("/"):return route.abort()
                        item=raw
                    else:item=access.get(request.url)
                    mime=item["mime"]
                    if not (mime.startswith(("image/","font/")) or mime in ("text/html","text/css","application/font-woff","application/vnd.ms-fontobject")):
                        return route.abort()
                    route.fulfill(status=200,body=item["content"],headers={"Content-Type":mime,
                        "Content-Security-Policy":"script-src 'none'; connect-src 'none'; frame-src 'none'; object-src 'none'; form-action 'none'; worker-src 'none'"})
                except Exception:route.abort()
            context.route("**/*",fulfill)
            for label,width,height in (("desktop",1440,1000),("mobile",390,844)):
                page=context.new_page();page.set_viewport_size({"width":width,"height":height})
                try:
                    page.goto(raw["url"],wait_until="load",timeout=30000)
                    # Native lazy loading is activated without executing any website JS.
                    page.locator('img[loading="lazy"]').evaluate_all("els => els.forEach(el => el.loading = 'eager')")
                    actual=page.locator("body").bounding_box() or {"height":height}
                    clipped=actual["height"]>16000
                    image=page.screenshot(type="jpeg",quality=72,full_page=not clipped,
                        **({"clip":{"x":0,"y":0,"width":width,"height":16000}} if clipped else {}),timeout=15000)
                    result.append({"viewport":label,"content":image,"mime":"image/jpeg","clipped":clipped,
                        "limitation":"Static public HTML rendering with scripts, embeds and video disabled. " + ("Capture capped at 16000 pixels tall." if clipped else "Full rendered page height captured.")})
                finally:page.close()
        finally:browser.close()
    return result
