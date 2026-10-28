import pytest
from app.mission import sample_plan,sample_source,validate_plan,technical_checks
from app.mission import normalize_quote


def test_plan_must_cite_exact_collected_text():
    plan=sample_plan();sources=[sample_source()]
    assert validate_plan(plan,sources)==plan
    plan["opportunities"][0]["quote"]="An invented quote that is not present"
    with pytest.raises(ValueError):validate_plan(plan,sources)


def test_unknown_source_cannot_pass_quote_validation():
    plan=sample_plan();plan["opportunities"][0]["source_id"]="S99"
    with pytest.raises(ValueError):validate_plan(plan,[sample_source()])


def test_inspector_reports_measurements_not_sales_claims():
    checks=technical_checks([sample_source()])
    assert len(checks)==4
    assert next(check for check in checks if check["name"]=="Inquiry forms")["passed"] is False
    assert all(check["source_id"]=="S1" for check in checks)


def test_quote_normalization_accepts_spacing_and_typography_only():
    assert normalize_quote('We\u00a0make “custom” parts — carefully.\nNext step')==normalize_quote('We make "custom" parts - carefully. Next   step')
    assert normalize_quote('MOQ 20-50')!=normalize_quote('MOQ 20-500')
    assert normalize_quote('We do not promise delivery')!=normalize_quote('We promise delivery')
    assert normalize_quote('Paid')!=normalize_quote('paid')
