def normalize_lang(raw):
    """Mirror static/js/i18n.js: any value starting with pt -> pt, else en."""
    if raw and str(raw).lower().startswith("pt"):
        return "pt"
    return "en"
