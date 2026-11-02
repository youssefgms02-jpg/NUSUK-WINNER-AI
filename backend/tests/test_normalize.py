from app.services import normalize

def test_normalize_ignores_case_and_whitespace():
    assert normalize(' ab 12-cd ') == 'AB12-CD'
