"""Bounded homepage snapshot prototype. Do not expose publicly without DNS pinning and egress filtering."""
import ipaddress
import socket
from urllib.parse import urlparse
from html.parser import HTMLParser
import httpx

class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.title = []
        self.in_title = False
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script","style","noscript"): self.skip += 1
        if tag == "title": self.in_title = True
    def handle_endtag(self, tag):
        if tag in ("script","style","noscript"): self.skip = max(0,self.skip-1)
        if tag == "title": self.in_title = False
    def handle_data(self, data):
        if self.skip: return
        txt = " ".join(data.split())
        if txt: (self.title if self.in_title else self.parts).append(txt)

def validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("https","http") or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None,80,443):
        raise ValueError("Only public HTTP(S) websites on standard ports are supported")
    host = parsed.hostname
    if host.lower() == "localhost" or host.lower().endswith((".local",".internal")):
        raise ValueError("Private host is not allowed")
    try:
        resolved = socket.getaddrinfo(host,parsed.port or (443 if parsed.scheme == "https" else 80),type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Website DNS lookup failed") from exc
    if not resolved or any(not ipaddress.ip_address(item[4][0]).is_global for item in resolved):
        raise ValueError("Website does not resolve exclusively to public addresses")
    return url

def snapshot(url: str) -> dict:
    validate_public_url(url)
    with httpx.Client(follow_redirects=False,timeout=8.0,trust_env=False,
                      headers={"User-Agent":"SentinelXResearch/0.3 (+website-audit)"}) as client:
        response = client.get(url,headers={"Accept":"text/html"})
    if response.is_redirect: raise ValueError("Redirects are not supported")
    response.raise_for_status()
    if "text/html" not in response.headers.get("content-type","").lower(): raise ValueError("Expected HTML page")
    if len(response.content) > 1_000_000: raise ValueError("Page exceeds 1 MB")
    page = PageText()
    page.feed(response.text)
    return {"url":url,"title":" ".join(page.title)[:200],"text":" ".join(page.parts)[:8000],"evidence_source":url}
