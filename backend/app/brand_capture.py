"""Robots-aware, pinned public retrieval and browser rendering with no direct browser egress."""
import hashlib
import re
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
# A business audit should focus on its homepage and the small set of pages
# that explain what it sells and how customers contact it.
MAX_PAGES=4


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
        super().__init__();self.base=base;self.links=[];self.link_labels={};self._anchor_url=None;self._anchor_text=[]
        self.images=[];self.contacts=[];self.description="";self.colors=[]

    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="a" and a.get("href"):
            href=a["href"]
            if href.startswith(("mailto:","tel:")):self.contacts.append(href[:200])
            elif len(self.links)<100:
                self._anchor_url=urljoin(self.base,href);self.links.append(self._anchor_url)
                self._anchor_text=[a.get("aria-label","")+" "+a.get("title","")]
        if tag=="img" and (a.get("src") or a.get("data-src")) and len(self.images)<30:
            label=(a.get("alt","")+" "+a.get("class","")+" "+a.get("id","")).strip()[:250]
            self.images.append({"url":urljoin(self.base,a.get("src") or a["data-src"]),"alt":label,"kind":"logo" if "logo" in label.lower() else "image"})
        if tag=="link" and "icon" in a.get("rel","").lower() and a.get("href"):
            self.images.append({"url":urljoin(self.base,a["href"]),"alt":"Website icon","kind":"logo"})
        if tag=="meta" and a.get("name","").lower()=="description":self.description=a.get("content","")[:1000]

    def handle_data(self,data):
        if self._anchor_url and data.strip():self._anchor_text.append(data.strip())

    def handle_endtag(self,tag):
        if tag=="a" and self._anchor_url:
            self.link_labels[self._anchor_url]=" ".join(self._anchor_text)[:200]
            self._anchor_url=None;self._anchor_text=[]


def page_details(raw):
    html=raw["content"].decode("utf-8",errors="replace")
    inventory=PageInventory(raw["url"]);inventory.feed(html)
    return {**inspect_html(html),"description":inventory.description,"links":inventory.links,
        "link_labels":inventory.link_labels,"images":inventory.images,"contacts":list(dict.fromkeys(inventory.contacts)),
        "sha256":hashlib.sha256(raw["content"]).hexdigest(),"url":raw["url"]}


def candidate_pages(urls,website,link_labels=None):
    host=(urlsplit(website).hostname or "").removeprefix("www.")
    link_labels=link_labels or {};candidates=[]
    for url in urls:
        try:url=clean_url(url)
        except ValueError:continue
        p=urlsplit(url)
        if (p.hostname or "").removeprefix("www.")!=host or p.query:continue
        path=p.path.lower().strip("/")
        if path in ("","index","index.html","home"):continue
        if any(piece in path for piece in ("login","account","cart","checkout","logout","wp-admin")):continue
        if p.path.lower().endswith((".pdf",".zip",".jpg",".png",".webp",".mp4")):continue
        label=link_labels.get(url,"").lower()
        target=(path+" "+label).replace("-"," ").replace("_"," ")
        if any(word in target for word in ("product","shop","collection","menu","catalog","catalogue")):
            category="products";priority=0
        elif any(word in target for word in ("service","what we do")):
            category="services";priority=1
        elif any(word in target for word in ("contact","get in touch","reach us","location","enquir","quote")):
            category="contact";priority=2
        else:
            # Do not spend a page slot on blogs, legal pages or arbitrary links.
            continue
        if all(existing[2]!=url for existing in candidates) and all(existing[1]!=category for existing in candidates):
            candidates.append((priority,category,url))
    return [url for _,_,url in sorted(candidates,key=lambda item:(item[0],item[2]))[:MAX_PAGES-1]]


def screenshots(raw,access):
    """Render a retrieved page offline while fetching its public assets safely.

    Site scripts may hydrate an otherwise empty app shell, but all requests are
    intercepted, robots checked and fetched through the pinned public retriever.
    The browser has no direct network, credentials, service workers, frames or
    form submission. Only anonymous same-site JSON GET requests may hydrate
    content; other API/XHR and arbitrary requests are blocked.
    """
    from playwright.sync_api import sync_playwright
    html=raw["content"].decode("utf-8",errors="replace")
    result=[]
    with sync_playwright() as runtime:
        browser=runtime.chromium.launch(headless=True,args=["--disable-dev-shm-usage"])
        try:
            context=browser.new_context(java_script_enabled=True,offline=True,service_workers="block",accept_downloads=False)
            def fulfill(route):
                request=route.request
                try:
                    if request.method!="GET" or request.resource_type not in ("document","image","stylesheet","font","script","xhr","fetch"):return route.abort()
                    if request.resource_type=="document":
                        if request.url.rstrip("/")!=raw["url"].rstrip("/"):return route.abort()
                        item=raw
                    elif request.resource_type in ("xhr","fetch"):
                        request_url=clean_url(request.url)
                        root=urlsplit(raw["url"]);target=urlsplit(request_url)
                        if target.hostname!=root.hostname or target.port not in (None,443):return route.abort()
                        item=access.get(request_url)
                        final=urlsplit(item["url"])
                        if final.hostname!=root.hostname or final.port not in (None,443):return route.abort()
                    else:item=access.get(request.url)
                    mime=item["mime"]
                    if request.resource_type in ("xhr","fetch") and mime not in ("application/json","text/json"):
                        return route.abort()
                    allowed=mime.startswith(("image/","font/")) or mime in (
                        "text/html","text/css","application/font-woff","application/vnd.ms-fontobject",
                        "application/javascript","text/javascript","application/x-javascript","application/json","text/json")
                    if not allowed:
                        return route.abort()
                    route.fulfill(status=200,body=item["content"],headers={"Content-Type":mime,
                        "Content-Security-Policy":"default-src 'none'; script-src https: 'unsafe-inline'; style-src https: 'unsafe-inline'; img-src https: data: blob:; font-src https: data:; connect-src 'self'; frame-src 'none'; object-src 'none'; form-action 'none'; worker-src 'none'; base-uri 'self'"})
                except Exception:route.abort()
            context.route("**/*",fulfill)
            for label,width,height in (("desktop",1440,1000),("mobile",390,844)):
                page=context.new_page();page.set_viewport_size({"width":width,"height":height})
                try:
                    page.goto(raw["url"],wait_until="load",timeout=20000)
                    try:page.wait_for_load_state("networkidle",timeout=5000)
                    except Exception:pass
                    page.wait_for_timeout(1200)
                    main=page.locator("main")
                    main_text=(main.inner_text(timeout=3000) if main.count() else page.locator("body").inner_text(timeout=3000)).strip()
                    visible_text=page.locator("body").inner_text(timeout=3000).strip()
                    placeholder=re.fullmatch(r"(?:loading|please wait|fetching|preparing)(?:[. …]*)",re.sub(r"\s+"," ",main_text).strip(),re.IGNORECASE)
                    if not main_text or (placeholder and len(main_text)<320):
                        raise ValueError("The page still shows a loading placeholder after isolated rendering; no misleading preview was saved.")
                    # Load images marked lazy after hydration, within the same routed context.
                    page.locator('img[loading="lazy"]').evaluate_all("els => els.forEach(el => el.loading = 'eager')")
                    actual=page.locator("body").bounding_box() or {"height":height}
                    clipped=actual["height"]>16000
                    image=page.screenshot(type="jpeg",quality=72,full_page=not clipped,
                        **({"clip":{"x":0,"y":0,"width":width,"height":16000}} if clipped else {}),timeout=15000)
                    links=page.locator("a[href]").evaluate_all("els => els.slice(0,100).map(a => ({url:a.href,label:(a.innerText||a.getAttribute('aria-label')||a.title||'').slice(0,200)}))")
                    result.append({"viewport":label,"content":image,"mime":"image/jpeg","clipped":clipped,
                        "visible_text":visible_text[:16000],"rendered_title":page.title()[:300],"rendered_links":links,
                        "limitation":"Isolated render. Public scripts and visual assets pass through the pinned, robots-aware retriever; only anonymous same-site JSON GETs are allowed for hydration. Other APIs, embeds and video are disabled. " + ("Capture capped at 16000 pixels tall." if clipped else "Rendered page height captured.")})
                finally:page.close()
        finally:browser.close()
    return result
