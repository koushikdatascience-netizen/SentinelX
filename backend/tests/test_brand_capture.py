import socket
from unittest.mock import Mock
import pytest
from app import brand_capture as capture


def test_public_access_is_robots_gated_and_platforms_are_not_scraped(monkeypatch):
    calls=[]
    def fake(url,maximum=2_000_000,**kwargs):
        calls.append(url)
        return {"url":url,"status":200,"mime":"text/plain","content":b"User-agent: *\nDisallow: /private"}
    monkeypatch.setattr(capture,"fetch_bytes",fake)
    access=capture.SiteAccess()
    with pytest.raises(ValueError,match="Access restricted"):access.get("https://example.org/private")
    with pytest.raises(ValueError):access.get("https://instagram.com/brand")
    assert calls==["https://example.org/robots.txt"]


def test_pinned_resolution_blocks_private_network_before_connect(monkeypatch):
    import app.public_web as public
    monkeypatch.setattr(socket,"getaddrinfo",lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,"",("127.0.0.1",443))])
    connect=Mock();monkeypatch.setattr(capture,"PinnedHTTPS",connect)
    with pytest.raises(ValueError,match="non-public"):capture.fetch_bytes("https://example.org/")
    connect.assert_not_called()


def test_inventory_is_source_content_and_prioritizes_relevant_same_site_pages():
    raw={"url":"https://example.org/","content":b'<title>Workshop</title><meta name="description" content="Custom parts"><a href="/products">Parts</a><a href="https://other.org/">Other</a><img src="/logo.png" alt="Brand logo"><a href="tel:123">Call</a>'}
    data=capture.page_details(raw)
    assert data["title"]=="Workshop" and data["images"][0]["kind"]=="logo"
    assert data["contacts"]==["tel:123"] and len(data["sha256"])==64
    assert capture.candidate_pages(data["links"]+["https://example.org/login","https://example.org/download.pdf"],raw["url"])==["https://example.org/products"]


def test_robots_failure_fails_closed(monkeypatch):
    monkeypatch.setattr(capture,"fetch_bytes",lambda *a,**k:{"status":503})
    assert not capture.SiteAccess().permitted("https://example.org/")


def test_failed_fetch_has_no_automatic_retry(monkeypatch):
    fake=Mock(side_effect=OSError("unavailable"));monkeypatch.setattr(capture,"fetch_bytes",fake)
    access=capture.SiteAccess();access.robots["https://example.org"]=None
    with pytest.raises(OSError):access.get("https://example.org/page")
    assert fake.call_count==1
