import io
import pytest
from openpyxl import Workbook
from app import business_data as data

CSV=b"Month,Region,Sales,Units\n2025-01-01,North,100.10,0\n2025-02-01,South,40.20,2\n2025-02-02,North,80.30,3\n"


def test_decimal_grouping_filters_dates_and_zero_values_are_exact():
    profile=data.profile(CSV,"sales.csv")
    assert profile["rows_analyzed"]==3 and profile["columns"][2]["sum"]=="220.60"
    result=data.calculate(CSV,"sales.csv",data.DataQuery(metric="Sales",group_by="Region"))
    assert result["results"]==[{"group":"North","value":"180.40"},{"group":"South","value":"40.20"}]
    filtered=data.calculate(CSV,"sales.csv",data.DataQuery(metric="Sales",filters=[data.DataFilter(column="Units",operator="eq",value="0")]))
    assert filtered["results"][0]["value"]=="100.10"
    months=data.calculate(CSV,"sales.csv",data.DataQuery(metric="Sales",group_by="Month",group_interval="month",sort="group_asc"))
    assert months["results"][0]["group"]=="2025-01" and months["results"][1]["value"]=="120.50"


def test_xlsx_and_utf16_csv_are_local_and_formulas_are_not_evaluated():
    book=Workbook();sheet=book.active;sheet.append(["Region","Sales"]);sheet.append(["North",100]);sheet.append(["South",40]);sheet.append(["Unknown","=1+2"])
    out=io.BytesIO();book.save(out)
    profile=data.profile(out.getvalue(),"sales.xlsx")
    assert profile["columns"][1]["sum"]=="140" and profile["rows_analyzed"]==3
    assert data.profile("Region,Sales\nNorth,10\n".encode("utf-16"),"sales.csv")["columns"][1]["sum"]=="10"


@pytest.mark.parametrize("payload",[b"",b"A,A\n1,2\n",b",B\n1,2\n"])
def test_invalid_headers_and_empty_files_fail_clearly(payload):
    with pytest.raises(ValueError):data.profile(payload,"data.csv")


def test_row_limits_and_unknown_columns_are_explicit(monkeypatch):
    monkeypatch.setattr(data,"MAX_ROWS",2)
    result=data.calculate(CSV,"sales.csv",data.DataQuery(metric="Sales"))
    assert result["truncated_input"] and result["rows_analyzed"]==2 and result["results"][0]["value"]=="140.30"
    with pytest.raises(ValueError,match="column"):data.calculate(CSV,"sales.csv",data.DataQuery(metric="not_a_column"))


def test_oversized_numeric_and_csv_fields_fail_safely():
    from app.business_data import numeric,table
    assert numeric("1e999999999")==None
    assert numeric("9"*1000)==None
    with pytest.raises(ValueError,match="oversized fields"):table(b"A\n"+b"x"*150000,"large.csv")
