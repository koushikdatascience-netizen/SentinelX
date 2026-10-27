from app.evidence import Recommendation, assess

def test_requires_review():
    item = Recommendation(claim='Website appears to lack a clear call to action', action='Review landing page copy with the business owner')
    result = assess(item)
    assert result['status'] == 'unverified'
    assert result['execution_performed'] is False
    assert result['approval_required'] is True
