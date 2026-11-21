"""Static quality gate behaviour."""

from __future__ import annotations

from tavola.brief import Brief
from tavola.quality import check_html


def _minimal() -> str:
    return (
        "<!DOCTYPE html><html><body>"
        '<h1 class="title">Title</h1>'
        '<p class="dek">Dek.</p>'
        '<footer class="colophon"><p class="bottom-line">Bottom.</p></footer>'
        "</body></html>"
    )


def test_minimal_page_passes() -> None:
    report = check_html(_minimal())
    assert report.passed
    assert report.issues == []


def test_script_tag_fails() -> None:
    report = check_html(_minimal() + "<script>alert(1)</script>")
    assert not report.passed
    assert any(issue.code == "script-tag" for issue in report.errors)


def test_external_reference_fails() -> None:
    report = check_html(_minimal().replace("</body>", '<img src="https://x/y.png"></body>'))
    assert not report.passed
    assert any(issue.code == "external-reference" for issue in report.errors)


def test_url_in_visible_text_fails() -> None:
    report = check_html(_minimal().replace("Dek.", "See https://example.com."))
    assert any(issue.code == "external-reference" for issue in report.errors)


def test_external_css_import_fails() -> None:
    report = check_html(_minimal().replace("</body>", "<style>@import url('https://x/y.css');</style></body>"))
    assert any(issue.code == "external-import" for issue in report.errors)


def test_empty_title_fails() -> None:
    report = check_html(_minimal().replace(">Title</h1>", ">   </h1>"))
    assert any(issue.code == "empty-title" for issue in report.errors)


def test_template_leftover_fails() -> None:
    report = check_html(_minimal() + "{{ left }}")
    assert any(issue.code == "template-leftover" for issue in report.errors)


def test_placeholder_warns_but_passes() -> None:
    report = check_html(_minimal().replace("Dek.", "Lorem ipsum dolor."))
    assert report.passed
    assert any(issue.severity == "warning" for issue in report.issues)


def test_inline_handler_fails() -> None:
    report = check_html(_minimal().replace("<body>", '<body onload="x()">'))
    assert any(issue.code == "inline-handler" for issue in report.errors)


def test_too_few_claims_flagged(brief: Brief) -> None:
    trimmed = brief.model_copy(deep=True)
    trimmed.claims = trimmed.claims[:2]
    report = check_html(_minimal(), brief=trimmed)
    assert any(issue.code == "too-few-claims" for issue in report.errors)

def test_data_uri_is_not_placeholder_text() -> None:
    html = (
        '<!doctype html><html><body><h1 class="title">T</h1>'
        '<p class="dek">D</p><footer class="colophon">'
        '<p class="bottom-line">B</p></footer>'
        '<img alt="" src="data:image/png;base64,TBD">'
        "</body></html>"
    )
    report = check_html(html)
    assert not any(issue.code == "placeholder-text" for issue in report.issues)
