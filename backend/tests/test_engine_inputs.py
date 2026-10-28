import io
import wave
import pytest
from app.engine_inputs import public_link,wav_duration,grounded_response,context_excerpt


def test_context_excerpt_retains_observations_and_unknowns_without_leading_metadata():
    original="> "+"Provenance metadata. "*40+"\n\nObserved turned wooden legs.\n"+"Scene detail. "*80+"\n> Product label remains quoted.\nUnknown: dimensions."
    excerpt=context_excerpt(original,True)
    assert excerpt.startswith("Observed turned wooden legs.")
    assert "Unknown: dimensions." in excerpt and "Product label remains quoted." in excerpt
    assert len(excerpt)<=520 and "[excerpt omitted]" in excerpt
    assert context_excerpt("> Owner-supplied quotation.")=="> Owner-supplied quotation."
    titled="**Grounded Visual Business Twin - Owner-Supplied File**\n\n"+original
    assert "Observed turned wooden legs." in context_excerpt(titled,True)
    assert "Provenance metadata." not in context_excerpt(titled,True)


def audio(channels=1,seconds=1):
    stream=io.BytesIO()
    with wave.open(stream,"wb") as clip:
        clip.setnchannels(channels);clip.setsampwidth(2);clip.setframerate(16000);clip.writeframes(b"\0\0"*16000*seconds*channels)
    return stream.getvalue()


def grounded():
    return {"id":"r1","object":"response","created_at":1,"model":"muse-spark-1.3","status":"completed",
        "output":[{"type":"web_search_call","id":"s1","status":"completed","results":[
            {"type":"text_result","title":"Candidate workshop","url":"https://example.org/","snippet":"Custom workshop components."}]},
            {"type":"message","id":"m1","role":"assistant","status":"completed","content":[
                {"type":"output_text","text":"A candidate workshop offers custom components.","annotations":[
                    {"type":"url_citation","url":"https://example.org/","title":"Candidate workshop","start_index":0,"end_index":20}]}]}]}


@pytest.mark.parametrize("url",["http://example.com/","https://127.0.0.1/","https://localhost/","https://user:pw@example.com/","javascript:alert(1)","https://169.254.169.254/"])
def test_citation_links_do_not_advertise_private_or_executable_urls(url):assert public_link(url) is False


def test_wav_limits_and_truncation_are_checked_before_any_inference():
    assert wav_duration(audio(),"audio/wav")==1000
    for payload,mime in [(audio(2),"audio/wav"),(audio(seconds=61),"audio/wav"),(audio()[:-20],"audio/wav"),(b"bad","audio/mpeg")]:
        with pytest.raises(ValueError):wav_duration(payload,mime)


def test_grounding_requires_real_search_and_valid_citation_spans():
    assert grounded_response(grounded())["searched"] is True
    data=grounded();data["output"][0]["status"]="failed"
    with pytest.raises(ValueError):grounded_response(data)
    data=grounded();data["output"][1]["content"][0]["annotations"][0]["end_index"]=10000
    with pytest.raises(ValueError):grounded_response(data)


def test_observed_live_search_results_are_not_misrepresented_as_inline_citations():
    data=grounded();data["output"][1]["content"][0]["annotations"]=[]
    result=grounded_response(data)
    assert result["searched"] is True and result["has_inline_citations"] is False
    assert result["citation_mode"]=="provider_results"
    assert result["citations"][0]["start_index"] is None and result["citations"][0]["url"]=="https://example.org/"
    assert "not span-cited" in result["limitation"]
    data["output"][0]["results"]=[]
    with pytest.raises(ValueError):grounded_response(data)
