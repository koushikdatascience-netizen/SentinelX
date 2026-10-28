import io
import zipfile
import pytest
from openpyxl import Workbook
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
from app.data_parser import parse_file


def pdf_bytes(text="Workshop handbook"):
    writer=PdfWriter();page=writer.add_blank_page(width=200,height=200)
    font=DictionaryObject({NameObject("/Type"):NameObject("/Font"),NameObject("/Subtype"):NameObject("/Type1"),NameObject("/BaseFont"):NameObject("/Helvetica")})
    page[NameObject("/Resources")]=DictionaryObject({NameObject("/Font"):DictionaryObject({NameObject("/F1"):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(("BT /F1 12 Tf 20 80 Td ("+text+") Tj ET").encode())
    page[NameObject("/Contents")]=writer._add_object(stream)
    target=io.BytesIO();writer.write(target);return target.getvalue()


def test_real_csv_quality_dates_and_units_without_currency_guessing():
    data=parse_file('date,product,amount\n2026-10-01,Leg,₹120.50\n2026-10-02,Leg,₹30\n2026-10-02,Leg,₹30\n2026-10-03,Panel,\n'.encode(),"csv")
    assert data["row_count"]==4 and data["duplicate_rows"]==1
    assert data["columns"][0]["type"]=="iso_date"
    assert data["columns"][2]["sum"]=="180.50" and data["columns"][2]["unit"]=="INR" and data["columns"][2]["missing"]==1
    mixed=parse_file(b'amount\nUSD 10\nINR 20\n',"csv")
    assert "sum" not in mixed["columns"][0] and "Mixed units" in mixed["columns"][0]["warning"]
    assert parse_file(b"part;units\nleg;4\npanel;2\n","csv")["columns"][1]["sum"]=="6"


def test_real_workbook_formulas_are_inert_and_not_fake_calculated():
    book=Workbook();sheet=book.active;sheet.append(["Product","Value"]);sheet.append(["Leg",12]);sheet.append(["Panel","=SUM(B2:B2)"])
    stream=io.BytesIO();book.save(stream)
    data=parse_file(stream.getvalue(),"xlsx")
    assert data["rows"][1][1]=="=SUM(B2:B2)" and data["formula_like_cells"]==1
    assert "sum" not in data["columns"][1]


def test_pdf_and_unicode_text_are_actually_extracted():
    data=parse_file(pdf_bytes(),"pdf")
    assert "Workshop handbook" in data["text"] and data["pages"][0]["page"]==1
    assert parse_file('বাংলা business notes'.encode(),"txt")["text"].startswith("বাংলা")
    assert parse_file("name,value\npart,20".encode("utf-16"),"csv")["encoding"]=="UTF-16 BOM"


@pytest.mark.parametrize("payload,extension",[(b"x"*2_000_001,"txt"),(b"a,a\n1,2","csv"),(b"a\n1,2","csv"),
    (b'[{"x":{"nested":1}}]',"json"),(b'[{"x":1},{"y":2}]',"json"),(b"not pdf","pdf"),(b"binary\0data","txt")],
    ids=["oversized","duplicate-headers","wide-row","nested-json","schema-mismatch","invalid-pdf","binary-text"])
def test_malformed_or_oversized_inputs_fail_closed(payload,extension):
    with pytest.raises(Exception):parse_file(payload,extension)


def test_zip_expansion_and_external_links_are_rejected_before_workbook_loading():
    for filename,content in [("xl/externalLinks/externalLink1.xml",b"external"),("huge",b"0"*2_000_000)]:
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,"w",compression=zipfile.ZIP_DEFLATED) as archive:archive.writestr(filename,content)
        with pytest.raises(ValueError):parse_file(stream.getvalue(),"xlsx")
