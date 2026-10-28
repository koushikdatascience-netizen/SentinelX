"""Bounded HTTPS requests with DNS validation and connection-time IP pinning.

No proxies, cookies, credentials, private addresses or automatic retries. Each
redirect gets its own DNS check. POST never follows redirects.
"""
import hashlib
import http.client
import ipaddress
import re
import socket
import ssl
import time
from threading import Timer
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

MAX_BYTES=1_000_000


def resolve_target(url):
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.port not in (None,443) or len(url)>2000):
        raise ValueError("Only public HTTPS URLs without credentials on port 443 are supported")
    host=parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
    if not re.fullmatch(r"[a-z0-9.-]+",host) or host=="localhost" or host.endswith((".local",".internal")):
        raise ValueError("Public domain required")
    rows=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
    if not rows:raise ValueError("DNS returned no addresses")
    for row in rows:
        address=ipaddress.ip_address(row[4][0])
        if not address.is_global or (getattr(address,"ipv4_mapped",None) and not address.ipv4_mapped.is_global):
            raise ValueError("DNS includes a non-public address")
        if getattr(address,"teredo",None) or getattr(address,"sixtofour",None):
            raise ValueError("IPv6 transition addresses are not supported")
    family,_,_,_,address=rows[0]
    return host,family,address,urlunsplit(("https",host,parsed.path or "/",parsed.query,""))


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self,host,family,address):
        super().__init__(host,443,timeout=8,context=ssl.create_default_context())
        self.family,self.address=family,address

    def connect(self):
        raw=socket.socket(self.family,socket.SOCK_STREAM)
        raw.settimeout(self.timeout)
        self.sock=raw
        try:
            # Connect directly to the validated numeric address, never resolve host again.
            raw.connect(self.address)
            self.sock=self._context.wrap_socket(raw,server_hostname=self.host,do_handshake_on_connect=False)
            self.sock.do_handshake()
        except BaseException:
            raw.close()
            raise


def request_public(url,*,method="GET",body=None,content_types=("text/html",),same_host=None,allow_url=None):
    if method not in ("GET","POST"):raise ValueError("Unsupported method")
    for redirect in range(3):
        host,family,address,normalized=resolve_target(url)
        if same_host is not None and host!=same_host:raise ValueError("Redirect left the authorized host")
        if allow_url is not None and not allow_url(normalized):raise ValueError("robots.txt disallows this target or redirect")
        parsed=urlsplit(normalized)
        path=parsed.path+("?"+parsed.query if parsed.query else "")
        connection=PinnedHTTPS(host,family,address)
        def abort(current=connection):
            sock=current.sock
            if sock:
                try:sock.shutdown(socket.SHUT_RDWR)
                except OSError:pass
                sock.close()
        deadline_timer=Timer(15,abort);deadline_timer.daemon=True;deadline_timer.start()
        try:
            headers={"Host":host,"Accept":"text/html","Accept-Encoding":"identity",
                     "User-Agent":"SentinelX/0.5 bounded owner-requested website review"}
            if body is not None:
                if not isinstance(body,bytes) or len(body)>8192:raise ValueError("Invalid form body")
                headers["Content-Type"]="application/x-www-form-urlencoded"
            connection.request(method,path,body=body,headers=headers)
            response=connection.getresponse()
            if response.status in (301,302,303,307,308):
                location=response.getheader("Location")
                if method!="GET" or not location or redirect==2:raise ValueError("Redirect not permitted")
                url=urljoin(normalized,location)
                continue
            if response.getheader("Content-Encoding", "identity").lower() not in ("identity",""):
                raise ValueError("Compressed responses are not supported")
            if int(response.getheader("Content-Length","0"))>MAX_BYTES:raise ValueError("Page exceeds 1 MB")
            content=bytearray();deadline=time.monotonic()+10
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise ValueError("Page retrieval exceeded time limit")
                if connection.sock:connection.sock.settimeout(min(8,remaining))
                chunk=response.read1(min(16384,MAX_BYTES+1-len(content)))
                if not chunk:break
                content.extend(chunk)
                if len(content)>MAX_BYTES:raise ValueError("Page exceeds 1 MB")
            content_type=response.getheader("Content-Type","").lower().split(";",1)[0].strip()
            if content_type not in content_types:raise ValueError("Unexpected content type")
            return {"url":normalized,"status":response.status,"html":content.decode("utf-8",errors="replace"),
                    "sha256":hashlib.sha256(content).hexdigest(),"bytes":len(content),
                    "collected_at":datetime.now(timezone.utc).isoformat()}
        finally:
            deadline_timer.cancel()
            connection.close()
    raise ValueError("Too many redirects")


class InspectHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text=[];self.title=[];self.in_title=False;self.skip=0
        self.media=[]
        self.signals={"forms":0,"phone_links":0,"email_links":0,"whatsapp_links":0,
                      "images":0,"images_without_alt":0,"h1_count":0,"viewport":False}

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ("script","style","noscript"):self.skip+=1
        if tag=="title":self.in_title=True
        if self.skip:return
        if tag=="form":self.signals["forms"]+=1
        if tag=="h1":self.signals["h1_count"]+=1
        if tag=="meta" and attrs.get("name", "").lower()=="viewport":self.signals["viewport"]=True
        if tag=="img":
            self.signals["images"]+=1
            if not (attrs.get("alt") or "").strip():self.signals["images_without_alt"]+=1
        if tag in ("img","video","source","iframe") and len(self.media)<30:
            url=attrs.get("src") or attrs.get("data-src")
            if url:self.media.append({"kind":tag,"url":url[:2000],"alt":(attrs.get("alt") or "")[:300],
                                     "content_analyzed":False})
        if tag=="a":
            href=(attrs.get("href") or "").lower()
            for key,prefix in (("phone_links","tel:"),("email_links","mailto:"),("whatsapp_links","https://wa.me/")):
                if href.startswith(prefix):self.signals[key]+=1

    def handle_endtag(self,tag):
        if tag in ("script","style","noscript"):self.skip=max(0,self.skip-1)
        if tag=="title":self.in_title=False

    def handle_data(self,data):
        if self.skip:return
        text=" ".join(data.split())
        if text:(self.title if self.in_title else self.text).append(text)


def inspect_html(html):
    parser=InspectHTML();parser.feed(html)
    return {"title":" ".join(parser.title)[:200],"text":" ".join(parser.text)[:6000],"signals":parser.signals,
            "media_inventory":parser.media}


def collect_page(url):
    page=request_public(url)
    if page["status"]!=200:raise ValueError("Website did not return HTTP 200")
    html=page.pop("html")
    return {**page,**inspect_html(html),"origin":"retrieved_public_page"}
