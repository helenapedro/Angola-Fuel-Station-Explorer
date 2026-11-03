"""Tests for error reports: validation and pre-filled issue URLs.

CI-safe: reports.py uses only the standard library, so no Dash,
Plotly or pandas import is needed here.
"""

import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import reports
from reports import Report, build_issue_url, build_report_links, validate_report

REPO = Path(__file__).resolve().parents[1]

KNOWN_IDS = {123, 456}

STATION = {
    "station": "KEU",
    "operator": "Unknown",
    "municipality": "",
    "province": "",
    "latitude": -5.5577802,
    "longitude": 12.1894286,
}


def _valid_report(**overrides):
    values = {
        "station_id": 123,
        "problem_type": "morada_errada",
        "details": "A morada está errada.",
        "source_url": "",
    }
    values.update(overrides)
    return Report(**values)


class ValidateReportTest(unittest.TestCase):
    def test_valid_report_has_no_errors(self):
        report = _valid_report()
        self.assertEqual(validate_report(report, KNOWN_IDS), [])
        self.assertEqual(report.errors, [])

    def test_unknown_station_id_rejected(self):
        report = _valid_report(station_id=999)
        self.assertTrue(validate_report(report, KNOWN_IDS))

    def test_non_numeric_station_id_rejected(self):
        report = _valid_report(station_id="abc")
        self.assertTrue(validate_report(report, KNOWN_IDS))

    def test_invalid_problem_type_rejected(self):
        report = _valid_report(problem_type="preco_errado")
        self.assertTrue(validate_report(report, KNOWN_IDS))

    def test_every_problem_type_accepted(self):
        for problem_type in reports.PROBLEM_TYPES:
            report = _valid_report(problem_type=problem_type)
            self.assertEqual(validate_report(report, KNOWN_IDS), [], problem_type)

    def test_details_over_500_chars_rejected(self):
        report = _valid_report(details="x" * 501)
        self.assertTrue(validate_report(report, KNOWN_IDS))

    def test_details_at_500_chars_accepted(self):
        report = _valid_report(details="x" * 500)
        self.assertEqual(validate_report(report, KNOWN_IDS), [])

    def test_html_stripped_before_length_check(self):
        report = _valid_report(details="<p>" + "x" * 500 + "</p>")
        self.assertEqual(validate_report(report, KNOWN_IDS), [])
        self.assertEqual(report.details, "x" * 500)
        self.assertNotIn("<p>", report.details)

    def test_source_url_must_start_with_https(self):
        report = _valid_report(source_url="http://example.com")
        self.assertTrue(validate_report(report, KNOWN_IDS))
        report = _valid_report(source_url="https://example.com/fonte")
        self.assertEqual(validate_report(report, KNOWN_IDS), [])

    def test_source_url_with_spaces_rejected(self):
        report = _valid_report(source_url="https://exa mple.com")
        self.assertTrue(validate_report(report, KNOWN_IDS))

    def test_empty_details_and_source_accepted(self):
        report = _valid_report(details="", source_url="   ")
        self.assertEqual(validate_report(report, KNOWN_IDS), [])
        self.assertEqual(report.source_url, "")


class BuildIssueUrlTest(unittest.TestCase):
    def test_url_contains_snapshot_station_and_problem(self):
        report = _valid_report(source_url="https://example.com/fonte")
        url = build_issue_url(report, STATION, "2026-09-23T11:27:12+00:00", "2026-09-23T11:27:12+00:00")
        parsed = urlparse(url)
        self.assertEqual(parsed.scheme, "https")
        self.assertTrue(parsed.path.endswith("/issues/new"))
        query = parse_qs(parsed.query)
        title = query["title"][0]
        body = query["body"][0]
        self.assertIn("123", title)
        self.assertIn("morada_errada", title)
        self.assertIn("KEU", body)
        self.assertIn("2026-09-23T11:27:12+00:00", body)
        self.assertIn("morada_errada", body)
        self.assertIn("A morada está errada.", body)
        self.assertIn("https://example.com/fonte", body)
        self.assertIn("-5.5577802, 12.1894286", body)
        self.assertEqual(query["labels"][0], "data-correction,morada_errada")

    def test_missing_snapshot_info_is_never_invented(self):
        report = _valid_report()
        url = build_issue_url(report, STATION, "indisponível", "indisponível")
        body = parse_qs(urlparse(url).query)["body"][0]
        self.assertIn("indisponível", body)

    def test_empty_fields_use_fallback_text(self):
        report = _valid_report(details="")
        url = build_issue_url(report, STATION, "2026-09-23T11:27:12+00:00", "2026-09-23T11:27:12+00:00")
        body = parse_qs(urlparse(url).query)["body"][0]
        self.assertIn("Sem detalhes", body)
        self.assertIn("Nenhuma", body)
        self.assertIn("Não disponível", body)


class BuildReportLinksTest(unittest.TestCase):
    def test_report_form_url_is_set_to_the_published_form(self):
        self.assertEqual(
            reports.REPORT_FORM_URL,
            "https://docs.google.com/forms/d/e/"
            "1FAIpQLSdkDQsxJ2FH67y6MdQM6690tknWiEyNc3TOGKzGoYI55UuvmA/viewform",
        )

    def test_no_form_url_means_github_only(self):
        report = _valid_report()
        links = build_report_links(
            report, STATION, "2026-09-23T11:27:12+00:00", "2026-09-23T11:27:12+00:00",
            form_url=None,
        )
        self.assertEqual(list(links), ["github_url"])

    def test_form_url_adds_the_plain_form_link(self):
        # No pre-fill parameters: the Forms API question IDs are not
        # the form's pre-fill entry IDs (verified in a real browser),
        # so the link stays plain until the real entry IDs are known.
        report = _valid_report()
        links = build_report_links(
            report, STATION, "2026-09-23T11:27:12+00:00", "2026-09-23T11:27:12+00:00",
            form_url=reports.REPORT_FORM_URL,
        )
        self.assertEqual(links["form_url"], reports.REPORT_FORM_URL)
        self.assertEqual(urlparse(links["form_url"]).query, "")


class NoSideEffectsTest(unittest.TestCase):
    def test_reports_module_has_no_io_or_network(self):
        source = (REPO / "reports.py").read_text(encoding="utf-8")
        for banned in ["open(", "requests", "urllib.request", "http.client", "subprocess", "import os", "from os", "os.path", "os.environ"]:
            self.assertNotIn(banned, source)


class StationIdFromSearchTest(unittest.TestCase):
    def test_parses_station_id_from_query_string(self):
        self.assertEqual(reports.station_id_from_search("?station_id=123"), 123)
        self.assertEqual(reports.station_id_from_search("station_id=456"), 456)

    def test_missing_or_invalid_station_id_returns_none(self):
        self.assertIsNone(reports.station_id_from_search(""))
        self.assertIsNone(reports.station_id_from_search(None))
        self.assertIsNone(reports.station_id_from_search("?station_id=abc"))
        self.assertIsNone(reports.station_id_from_search("?other=123"))


class ReportUiWiringTest(unittest.TestCase):
    def test_report_page_holds_the_form_and_validates_in_callback(self):
        page_source = (REPO / "pages" / "reportar_erro.py").read_text(encoding="utf-8")
        self.assertIn('path="/reportar-erro"', page_source)
        for component_id in ["report-problem-type", "report-details", "report-source-url", "report-submit", "report-output", "report-station-id", "report-station-select"]:
            self.assertIn(component_id, page_source)
        self.assertIn("validate_report", page_source)
        self.assertIn("build_report_links", page_source)
        self.assertIn("REPORT_FORM_URL", page_source)
        self.assertNotIn("issues/new", page_source)

    def test_home_page_has_only_a_report_button_not_the_form(self):
        layout_source = (REPO / "map_dashboard" / "layout.py").read_text(encoding="utf-8")
        self.assertNotIn("report-problem-type", layout_source)
        self.assertNotIn("report-submit", layout_source)
        presentation_source = (REPO / "map_dashboard" / "presentation.py").read_text(encoding="utf-8")
        self.assertIn("Reportar erro", presentation_source)
        self.assertIn("/reportar-erro?station_id=", presentation_source)
        map_source = (REPO / "pages" / "map.py").read_text(encoding="utf-8")
        self.assertNotIn("report-submit", map_source)
        self.assertNotIn("validate_report", map_source)


if __name__ == "__main__":
    unittest.main()
