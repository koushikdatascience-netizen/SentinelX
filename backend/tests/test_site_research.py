import hashlib
import pytest
from app import site_research
from app.site_research import canonical_url,analyze_page,sitemap_urls,crawl,findings


HOME='<title>Workshop</title><h1>Made-to-order parts</h1><p>We manufacture wooden components for furniture makers and trade buyers.</p><a href="/products">Products</a><a href="/private">Private</a><a href="https://instagram.com/workshop">Instagram</a><a href="tel:123">Call</a><a href="mailto:office@example.com">Email</a><img src="part.png">'


def response(url,text,status=200):
    return {"url":url,"html":text,"status":status,"sha256":hashlib.sha256(text.encode()).hexdigest(),"bytes":len(text),"collected_at":"2026-10-28T00:00:00+00:00"}


def fake_site(monkeypatch,robots="User-agent: *\nDisallow: /private",sitemap=None):
    calls=[]
    def request(url,**kwargs):
        calls.append((url,kwargs));assert kwargs["same_host"] in ("example.com","other.example.org")
        if url.endswith("robots.txt"):return response(url,robots)
        if url.endswith("sitemap.xml"):return response(url,sitemap or '<urlset><url><loc>https://example.com/contact</loc></url></urlset>')
        if url.endswith("/private"):pytest.fail("Robots-disallowed page was fetched")
        return response(url,HOME if url.endswith("/") else '<title>Product information</title><h1>Wooden legs</h1><p>Bulk workshop parts with custom measurements by quotation.</p>')
    monkeypatch.setattr(site_research,"request_public",request)
    return calls


def state():return {"queue":[["https://example.com/",0,"business"]],"pages":[],"errors":[],"visited":[],"limitations":[],"requests":0,"max_pages":5,"max_depth":2}


def test_navigation_sitemap_robots_and_evidence_are_real_deterministic_processing(monkeypatch):
    calls=fake_site(monkeypatch);data=state();snapshots=[]
    assert crawl(data,lambda value:snapshots.append(len(value["pages"])),lambda:False,pause=lambda _:None)=="completed"
    assert {page["url"] for page in data["pages"]}=={"https://example.com/","https://example.com/products","https://example.com/contact"}
    assert any("robots" in error["reason"] for error in data["errors"])
    page=data["pages"][0]
    assert page["profiles"][0]["verification"]=="website_linked_candidate" and not page["profiles"][0]["identity_confirmed"]
    assert page["contacts"]["emails"]==["office@example.com"]
    assert any(item["finding"]=="Images missing descriptions" for item in findings(page))
    assert len(page["sha256"])==64 and len(snapshots)>=3
    assert all("instagram.com" not in url for url,_ in calls)


@pytest.mark.parametrize("url",["https://localhost/","https://127.0.0.1/","file:///etc/passwd","https://user:pass@example.com/","https://example.com:444/","https://[invalid/","https://example.com/?delete=1"])
def test_discovery_discards_unsafe_or_unbounded_links(url):assert canonical_url(url) is None


def test_sitemap_entities_and_foreign_hosts_are_rejected():
    assert sitemap_urls('<urlset><url><loc>https://other.org/</loc></url><url><loc>https://example.com/p</loc></url></urlset>',"example.com")==["https://example.com/p"]
    with pytest.raises(Exception):sitemap_urls('<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><urlset>&e;</urlset>',"example.com")


def test_cancellation_and_page_bounds_do_not_invent_completion(monkeypatch):
    calls=fake_site(monkeypatch);data=state()
    assert crawl(data,lambda _:None,lambda:True,pause=lambda _:None)=="cancelled" and calls==[]
    data["max_pages"]=1
    assert crawl(data,lambda _:None,lambda:False,pause=lambda _:None)=="completed"
    assert len(data["pages"])==1 and data["queue"]
    assert data["requests"]==3


def test_unavailable_robots_blocks_host_and_reports_failure(monkeypatch):
    seen=[]
    def unavailable(url,**kwargs):seen.append(url);return response(url,"Unavailable",503)
    monkeypatch.setattr(site_research,"request_public",unavailable)
    data=state();assert crawl(data,lambda _:None,lambda:False,pause=lambda _:None)=="failed"
    assert seen==["https://example.com/robots.txt"] and data["pages"]==[]


def test_schema_and_platform_identity_are_not_guessed():
    page=analyze_page(response("https://example.com/",'<script type="application/ld+json">{broken}</script><a href="https://instagram.com.evil.org/fake">Fake</a>'),"business")
    assert page["profiles"]==[] and page["structured_data"][0]["valid_json"] is False
    assert any(item["finding"]=="Invalid JSON-LD" for item in findings(page))


def test_jsonld_identity_and_sameas_are_extracted_as_unverified_claims():
    text='<script type="application/ld+json">{"@type":"LocalBusiness","name":"Workshop","address":{"addressLocality":"Kalyani"},"sameAs":["https://facebook.com/workshop"]}</script>'
    page=analyze_page(response("https://example.com/",text),"business")
    assert page["structured_claims"][0]["value"]=="Workshop"
    assert page["profiles"][0]["platform"]=="Facebook" and page["profiles"][0]["identity_confirmed"] is False


def test_brand_images_are_inventory_candidates_not_claimed_as_analyzed():
    text='<meta property="og:image" content="/brand/logo.webp"><link rel="icon" href="/favicon.png"><img src="/product.jpg" alt="Wooden chair">'
    page=analyze_page(response("https://example.com/",text),"business")
    assets=page["media_inventory"]
    assert assets[0]["role"]=="probable_logo_or_brand_art" and assets[0]["visual_review_available"]
    assert all(item["content_analyzed"] is False for item in assets)
