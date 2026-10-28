import io
import socket
from unittest.mock import Mock
import pytest
from app import public_web


@pytest.mark.parametrize("url",["http://example.com","https://user:pass@example.com","https://localhost/",
    "https://test.internal/","https://example.com:444/","https://[::1]/"])
def test_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):public_web.resolve_target(url)


@pytest.mark.parametrize("addresses",[["127.0.0.1"],["169.254.169.254"],["10.0.0.2"],
    ["8.8.8.8","192.168.1.2"],["::ffff:127.0.0.1"]])
def test_rejects_all_mixed_or_private_dns(monkeypatch,addresses):
    monkeypatch.setattr(socket,"getaddrinfo",lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,0,"",(ip,443)) for ip in addresses])
    with pytest.raises(ValueError):public_web.resolve_target("https://example.com/")


def test_connect_pins_ip_and_uses_original_tls_hostname(monkeypatch):
    raw=Mock();context=Mock()
    monkeypatch.setattr(socket,"socket",lambda *a:raw)
    connection=public_web.PinnedHTTPS("example.com",socket.AF_INET,("8.8.8.8",443))
    assert connection._context.check_hostname is True
    connection._context=context
    connection.connect()
    raw.connect.assert_called_once_with(("8.8.8.8",443))
    context.wrap_socket.assert_called_once_with(raw,server_hostname="example.com",do_handshake_on_connect=False)
    context.wrap_socket.return_value.do_handshake.assert_called_once()


def response(monkeypatch,*,status=200,headers=None,html=b"<title>Workshop</title><p>We make furniture.</p>"):
    monkeypatch.setattr(socket,"getaddrinfo",lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,0,"",("8.8.8.8",443))])
    stream=io.BytesIO(html);reply=Mock(status=status)
    values={"Content-Type":"text/html",**(headers or {})}
    reply.getheader=lambda name,default=None:values.get(name,default)
    reply.read1=stream.read1
    connection=Mock(sock=None);connection.getresponse.return_value=reply
    monkeypatch.setattr(public_web,"PinnedHTTPS",lambda *a:connection)
    return connection


def test_snapshot_contains_real_hash_and_structural_signals(monkeypatch):
    connection=response(monkeypatch,html=b'<title>Workshop</title><meta name="viewport" content="width=device-width"><h1>Furniture</h1><script>ignore this fake form</script><form></form><a href="tel:123">Call</a><img alt="chair">')
    page=public_web.collect_page("https://example.com")
    assert page["origin"]=="retrieved_public_page" and len(page["sha256"])==64
    assert page["signals"]["forms"]==1 and page["signals"]["phone_links"]==1
    assert page["signals"]["viewport"] and page["signals"]["images_without_alt"]==0
    assert "ignore" not in page["text"]
    connection.close.assert_called_once()


def test_redirect_to_private_ip_is_revalidated(monkeypatch):
    response(monkeypatch,status=302,headers={"Location":"https://localhost/admin"})
    with pytest.raises(ValueError):public_web.collect_page("https://example.com")


@pytest.mark.parametrize("headers",[{"Content-Length":"1000001"},{"Content-Encoding":"gzip"},{"Content-Type":"application/json"}])
def test_rejects_unbounded_or_non_html_content(monkeypatch,headers):
    response(monkeypatch,headers=headers)
    with pytest.raises(ValueError):public_web.collect_page("https://example.com")


def test_stream_size_is_bounded_without_content_length(monkeypatch):
    response(monkeypatch,html=b"x"*1_000_001)
    with pytest.raises(ValueError):public_web.collect_page("https://example.com")


def test_post_never_follows_redirects(monkeypatch):
    connection=response(monkeypatch,status=307,headers={"Location":"https://example.com/elsewhere"})
    with pytest.raises(ValueError):public_web.request_public("https://example.com/form",method="POST",body=b"name=test")
    assert connection.request.call_count==1


def test_research_redirect_scope_and_explicit_document_types(monkeypatch):
    connection=response(monkeypatch,status=302,headers={"Location":"https://other.org/"})
    with pytest.raises(ValueError):public_web.request_public("https://example.com/",same_host="example.com")
    assert connection.request.call_count==1
    response(monkeypatch,headers={"Content-Type":"text/plain"},html=b"User-agent: *\nDisallow: /private")
    result=public_web.request_public("https://example.com/robots.txt",content_types=("text/plain",),same_host="example.com")
    assert "Disallow" in result["html"]


def test_research_redirect_cannot_escape_robots_policy(monkeypatch):
    connection=response(monkeypatch,status=302,headers={"Location":"https://example.com/private"})
    with pytest.raises(ValueError,match="robots"):
        public_web.request_public("https://example.com/",same_host="example.com",allow_url=lambda target:not target.endswith("/private"))
    assert connection.request.call_count==1
