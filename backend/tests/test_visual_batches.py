import hashlib
import io
import pytest
from PIL import Image
from app.visual_batches import prepare_batch


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
