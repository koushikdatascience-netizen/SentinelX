import io
import zipfile
import pytest
from app.business_files import validate_upload


def test_text_document_preserves_bounded_excerpt():
    name,mime,metadata=validate_upload(b"Business brochure\nCustom work available","../brochure.txt","document")
    assert name=="brochure.txt" and mime=="text/plain"
    assert "Custom work" in metadata["text_excerpt"]


def test_docx_and_xlsx_extract_text_without_executing_content():
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w") as archive:archive.writestr("word/document.xml",'<root><text>Business catalogue</text></root>')
    assert validate_upload(out.getvalue(),"catalogue.docx","document")[2]["text_excerpt"]=="Business catalogue"
    from openpyxl import Workbook
    book=Workbook();book.active.append(["Product"]);book.active.append(["Business catalogue"])
    out=io.BytesIO();book.save(out)
    metadata=validate_upload(out.getvalue(),"catalogue.xlsx","document")[2]
    assert "Business catalogue" in metadata["text_excerpt"]
    assert metadata["dataset_profile"]["rows_analyzed"]==1


def test_incomplete_xlsx_archive_is_rejected_before_dataset_use():
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w") as archive:archive.writestr("xl/sharedStrings.xml",'<root>Incomplete workbook</root>')
    with pytest.raises(ValueError,match="workbook could not be read"):validate_upload(out.getvalue(),"bad.xlsx","knowledge")


@pytest.mark.parametrize("name,payload",[("app.exe",b"MZpayload"),("bad.pdf",b"not a PDF"),("bad.docx",b"not a zip"),("bad.txt",b"\x00binary"),("logo.png",b"broken")])
def test_rejects_unsupported_or_malformed_files(name,payload):
    with pytest.raises(ValueError):validate_upload(payload,name,"document")


def test_rejects_macro_office_document():
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w") as archive:
        archive.writestr("word/document.xml","<root>text</root>")
        archive.writestr("word/vbaProject.bin",b"macro")
    with pytest.raises(ValueError,match="macro"):validate_upload(out.getvalue(),"bad.docx","document")
