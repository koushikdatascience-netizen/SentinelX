import io
import zipfile
import pytest
from app.business_files import validate_upload


def test_text_document_preserves_bounded_excerpt():
    name,mime,metadata=validate_upload(b"Business brochure\nCustom work available","../brochure.txt","document")
    assert name=="brochure.txt" and mime=="text/plain"
    assert "Custom work" in metadata["text_excerpt"]


def test_docx_and_xlsx_extract_text_without_executing_content():
    for suffix,target in (("docx","word/document.xml"),("xlsx","xl/sharedStrings.xml")):
        out=io.BytesIO()
        with zipfile.ZipFile(out,"w") as archive:archive.writestr(target,'<root><text>Business catalogue</text></root>')
        assert validate_upload(out.getvalue(),"catalogue."+suffix,"document")[2]["text_excerpt"]=="Business catalogue"


@pytest.mark.parametrize("name,payload",[("app.exe",b"MZpayload"),("bad.pdf",b"not a PDF"),("bad.docx",b"not a zip"),("bad.txt",b"\x00binary"),("logo.png",b"broken")])
def test_rejects_unsupported_or_malformed_files(name,payload):
    with pytest.raises(ValueError):validate_upload(payload,name,"document")


def test_rejects_macro_office_document():
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w") as archive:
        archive.writestr("word/document.xml","<root>text</root>")
        archive.writestr("word/vbaProject.bin",b"macro")
    with pytest.raises(ValueError,match="macro"):validate_upload(out.getvalue(),"bad.docx","document")
