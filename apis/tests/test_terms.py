from app.services.terms import (
    albert_term_label,
    class_term_filter,
    flexible_term_filter,
    normalize_term_label,
    normalize_term_code,
    term_code_to_label,
    term_label_to_code,
)


def test_term_code_to_label_uses_nyu_digit_convention():
    assert term_code_to_label("1272") == "Winter 2027"
    assert term_code_to_label("1274") == "Spring 2027"
    assert term_code_to_label("1276") == "Summer 2027"
    assert term_code_to_label("1278") == "Fall 2027"


def test_term_label_to_code_uses_nyu_digit_convention():
    assert term_label_to_code("Winter 2027") == "1272"
    assert term_label_to_code("Spring 2027") == "1274"
    assert term_label_to_code("Summer 2027") == "1276"
    assert term_label_to_code("Fall 2027") == "1278"


def test_unknown_terms_pass_through():
    assert term_code_to_label("9999") is None
    assert term_label_to_code("Maymester 2027") is None
    assert albert_term_label("Maymester 2027") == "Maymester 2027"
    assert normalize_term_code("Maymester 2027") == "Maymester 2027"


def test_term_labels_normalize_case():
    assert normalize_term_label("fall 2027") == "Fall 2027"
    assert albert_term_label("summer 2027") == "Summer 2027"
    assert normalize_term_code("winter 2027") == "1272"


def test_class_filters_accept_codes_and_labels():
    assert class_term_filter("1278", "albert") == {"term": "Fall 2027"}
    assert class_term_filter("Fall 2027", "bulletin") == {"term.code": "1278"}


def test_flexible_filter_includes_code_and_albert_label():
    assert flexible_term_filter("1272") == {
        "$or": [{"term.code": "1272"}, {"term": "Winter 2027"}]
    }
