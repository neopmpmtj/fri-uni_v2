from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from weasyprint import HTML

from .quote_i18n import quote_labels


COMPANY_NAME = "fri-uni"


def build_proforma_pdf(proforma, lang="en"):
    html = render_to_string(
        "proformas/quote_pdf.html",
        {
            "proforma": proforma,
            "lines": proforma.lines.all(),
            "labels": quote_labels(lang),
            "company_name": COMPANY_NAME,
            "html_lang": "pt-PT" if lang == "pt" else "en",
        },
    )
    try:
        return HTML(string=html).write_pdf()
    except OSError as exc:
        raise ValidationError("Could not generate PDF.") from exc
