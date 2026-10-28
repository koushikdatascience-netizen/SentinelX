import hashlib
import io
import pytest
from PIL import Image
from app.visual_batches import prepare_batch,validate_vision_output


def png(color=(40,90,140),size=(120,80)):
    output=io.BytesIO();Image.new("RGB",size,color).save(output,format="PNG");return output.getvalue()


def test_prepare_batch_keeps_only_hash_and_measurements_in_result():
    payload=png();digest=hashlib.sha256(payload).hexdigest()
    prepared=prepare_batch([{"body":payload,"mime":"image/png","sha256":digest,"source":"owner_supplied_screenshot"}])
    assert prepared["batch_key"]==hashlib.sha256(digest.encode()).hexdigest()
    assert prepared["images"][0]["sha256"]==digest
    assert prepared["images"][0]["source"]=="owner_supplied_screenshot"
    assert "body" not in prepared["images"][0]
    assert prepared["contact_sheet"].startswith(b"\xff\xd8")


def test_prepare_batch_enforces_count_bytes_and_mime():
    payload=png()
    with pytest.raises(ValueError,match="1 to 4"):
        prepare_batch([{"body":payload,"mime":"image/png"}]*5)
    with pytest.raises(ValueError,match="type does not match"):
        prepare_batch([{"body":payload,"mime":"image/jpeg"}])
    with pytest.raises(ValueError,match="2.5 MB"):
        prepare_batch([{"body":b"x"*2_500_001,"mime":"image/png"}])

def test_supplied_hash_must_match_actual_image_bytes():
    payload=png()
    with pytest.raises(ValueError,match="SHA-256 does not match"):
        prepare_batch([{"body":payload,"mime":"image/png","sha256":"0"*64}])
    computed=prepare_batch([{"body":payload,"mime":"image/png","sha256":hashlib.sha256(payload).hexdigest().upper()}])
    assert computed["images"][0]["sha256"]==hashlib.sha256(payload).hexdigest()

def finding(index):
    return {"image_index":index,"observation":f"Image {index} shows visible wood grain.",
        "suggested_improvement":f"Use image {index} with a concise product label."}

def test_structured_vision_output_is_ordered_and_keeps_summary_separate():
    data={"findings":[finding(2),finding(1)],"summary":"The selected images share warm tones."}
    parsed=validate_vision_output(data,2)
    assert [item["image_index"] for item in parsed["findings"]]==[1,2]
    assert parsed["summary"]=="The selected images share warm tones."

@pytest.mark.parametrize("data,expected",[
    ({"findings":[finding(1)],"summary":"A valid summary."},"one finding"),
    ({"findings":[finding(2),finding(2)],"summary":"A valid summary."},"duplicate"),
    ({"findings":[{"image_index":1,"observation":"Only an observation."},finding(2)],"summary":"A valid summary."},"invalid structure"),
    ({"findings":[finding(1),finding(3)],"summary":"A valid summary."},"out-of-range"),
    ({"findings":[finding(True),finding(2)],"summary":"A valid summary."},"out-of-range"),
    ({"findings":[finding(1),finding(2)],"summary":""},"summary"),
])
def test_structured_vision_rejects_missing_duplicate_and_malformed_mappings(data,expected):
    with pytest.raises(ValueError,match=expected):validate_vision_output(data,2)


def test_rejects_duplicate_image_bytes_within_single_batch():
    payload=png()
    with pytest.raises(ValueError,match="duplicate image bytes"):
        prepare_batch([{"body":payload,"mime":"image/png"},{"body":payload,"mime":"image/png"}])
