from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from weasyprint import HTML


def build_proforma_pdf(proforma, lang="en"):
    from .services import quote_template_context

    html = render_to_string(
        "proformas/quote_pdf.html",
        quote_template_context(proforma, lang, absolute_logo=True),
    )
    try:
        return HTML(string=html).write_pdf()
    except Exception as exc:
        raise ValidationError("Could not generate PDF.") from exc
