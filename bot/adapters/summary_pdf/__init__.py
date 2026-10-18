"""The summary PDF sent to the mailing list.

    renderer.py     SummaryPdfRenderer.render — lays out one letter's summary PDF (an Extraction), section by section
    flow_chart.py   flow_chart — the sources -> hubs -> destinations picture of the money
    money_flow.py   transfer_summary / hubs / fold — where the money comes from and goes (no drawing)
    theme.py        the font, colors and money format the page and the chart share
    hebrew_text.py  rtl / wrap_rtl_html — Hebrew put into visual order for reportlab, which has no bidi
    fonts/          Arimo (Hebrew + Latin) and its license
"""
