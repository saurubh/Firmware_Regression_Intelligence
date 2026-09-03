"""
Firmware Regression Intelligence (FRI)

HTML Report Generator

Renders a RegressionReport into an HTML dashboard.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from fri.constants import (
    HTML_REPORT,
    TEMPLATE_DIR,
)


class HtmlReport:
    """
    Generates an HTML dashboard from a RegressionReport.
    """

    def __init__(self):

        self.environment = Environment(

            loader=FileSystemLoader(TEMPLATE_DIR),

            autoescape=select_autoescape(

                enabled_extensions=("html",)

            )

        )

        self.template = self.environment.get_template(

            "dashboard.html"

        )

    # ======================================================

    def render(self, report, top: int = 10):

        html = self.template.render(

            report=report,

            statistics=report.statistics,

            candidates=report.candidates[:top],

            modules=report.modules,

            bisect=report.bisect,

            generated=report.generated_at,

        )

        output = Path(HTML_REPORT)

        output.parent.mkdir(

            parents=True,

            exist_ok=True

        )

        output.write_text(

            html,

            encoding="utf-8"

        )

        return output