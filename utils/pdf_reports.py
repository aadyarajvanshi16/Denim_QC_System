"""
PDF report builders, pulled out of app.py so the routes stay thin.
Behavior matches the original reports (same sections/tables); the
data now comes from an Inspection/RecipeExtraction row instead of
scattered app.config globals.
"""

from __future__ import annotations

import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.drawString(40, 20, datetime.now().strftime("%d-%m-%Y %H:%M"))
    canvas.restoreState()


def build_inspection_report(inspection, pdf_path: str) -> str:
    """inspection: a models.Inspection row."""
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("AI Denim Dye Inspection Report", styles["Title"]))
    elements.append(Spacer(1, 10))

    details = [
        ["Comparison ID", inspection.comp_id],
        ["Inspection Time", inspection.created_at.strftime("%d-%m-%Y %H:%M")],
        ["Reference Fabric", inspection.reference_filename or "-"],
        ["Test Fabric", inspection.test_filename or "-"],
        ["Delta E", str(inspection.delta_e)],
        ["QC Status", inspection.status],
    ]

    elements.append(Paragraph("Detailed LAB Analysis", styles["Heading2"]))
    elements.append(Spacer(1, 12))

    advanced_data = [
        ["Parameter", "Reference", "Test"],
        ["L Value", str(inspection.lab1_l), str(inspection.lab2_l)],
        ["A Value", str(inspection.lab1_a), str(inspection.lab2_a)],
        ["B Value", str(inspection.lab1_b), str(inspection.lab2_b)],
        ["Similarity %", str(inspection.similarity), "-"],
        ["AI Confidence", str(inspection.confidence), "-"],
    ]
    advanced_table = Table(advanced_data, colWidths=[180, 150, 150])
    advanced_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ]
        )
    )
    elements.append(advanced_table)
    elements.append(Spacer(1, 10))

    table = Table(details, colWidths=[180, 300])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("ROI Images and LAB Analysis", styles["Heading2"]))
    elements.append(Spacer(1, 12))

    row = []
    if inspection.ref_roi_path and os.path.isfile(inspection.ref_roi_path):
        row.append(Image(inspection.ref_roi_path, width=120, height=120))
    if inspection.test_roi_path and os.path.isfile(inspection.test_roi_path):
        row.append(Image(inspection.test_roi_path, width=120, height=120))
    if inspection.bar_chart:
        bar_chart_path = os.path.join("static/results", inspection.bar_chart)
        if os.path.isfile(bar_chart_path):
            row.append(Image(bar_chart_path, width=220, height=120))

    if row:
        combined_table = Table([row])
        combined_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOX", (0, 0), (-1, -1), 1, colors.black),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        elements.append(combined_table)
        elements.append(Spacer(1, 15))

    elements.append(PageBreak())
    elements.append(Paragraph("AI Industrial Interpretation", styles["Heading2"]))
    elements.append(
        Paragraph(
            "• Delta E comparison indicates overall color consistency.<br/>"
            "• LAB values provide perceptual color measurements.<br/>"
            "• ROI based analysis eliminates background interference.<br/>"
            "• Computer vision identifies dominant denim shades.<br/>"
            "• AI-assisted inspection improves repeatability and quality control.",
            styles["BodyText"],
        )
    )
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("Quality Assessment", styles["Heading2"]))
    elements.append(
        Paragraph(
            f"Inspection Status : {inspection.status}<br/>"
            f"Similarity Score : {inspection.similarity} %<br/>"
            f"AI Confidence : {inspection.confidence} %<br/>"
            f"Delta E Value : {inspection.delta_e}<br/>",
            styles["BodyText"],
        )
    )
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("Industrial Observations", styles["Heading2"]))
    elements.append(
        Paragraph(
            "• Suitable for denim shade consistency evaluation.<br/>"
            "• Helps detect dye variation between batches.<br/>"
            "• Supports textile quality control workflows.<br/>"
            "• Reduces manual inspection effort.<br/>"
            "• Improves production reliability.<br/>",
            styles["BodyText"],
        )
    )
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("Recommendation", styles["Heading2"]))
    if inspection.status == "PASS":
        recommendation = (
            "AI recommends accepting this fabric sample for production as the "
            "color variation is within the acceptable tolerance range."
        )
    else:
        recommendation = (
            "AI recommends rejecting this sample due to excessive color "
            "deviation from the reference fabric."
        )
    elements.append(Paragraph(recommendation, styles["BodyText"]))
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("Report Information", styles["Heading2"]))
    meta = [
        ["Generated By", "IoTrenetics Solutions AI Textile Intelligence System"],
        ["Report Type", "Industrial Denim QC Report"],
        ["Generated On", datetime.now().strftime("%d-%m-%Y %H:%M:%S")],
    ]
    meta_table = Table(meta, colWidths=[130, 320])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 10))
    elements.append(
        Paragraph(
            f"Generated by IoTrenetics Solutions AI Textile Intelligence System",
            styles["Italic"],
        )
    )

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    return pdf_path


def build_recipe_report(recipe_extraction, pdf_path: str) -> str:
    """recipe_extraction: a models.RecipeExtraction row."""
    import json

    doc = SimpleDocTemplate(
        pdf_path, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
    )
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("AI Dye Recipe Extraction Report", styles["Title"]))
    elements.append(Spacer(1, 8))

    details = [
        ["Generated On", recipe_extraction.created_at.strftime("%d-%m-%Y %H:%M")],
        ["Inspection Type", "Single Fabric Recipe Extraction"],
        ["AI Engine", "LAB + Dominant Shade Analysis"],
    ]
    table = Table(details, colWidths=[150, 220])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 10))

    if recipe_extraction.roi_path and os.path.isfile(recipe_extraction.roi_path):
        elements.append(Paragraph("Selected ROI Fabric Region", styles["Heading2"]))
        elements.append(Spacer(1, 10))
        elements.append(Image(recipe_extraction.roi_path, width=300, height=300))
        elements.append(Spacer(1, 10))

    elements.append(Paragraph("LAB Color Analysis", styles["Heading2"]))
    elements.append(Spacer(1, 10))
    lab = recipe_extraction.lab()
    lab_data = [["Channel", "Value"], ["L", str(lab[0])], ["A", str(lab[1])], ["B", str(lab[2])]]
    lab_table = Table(lab_data, colWidths=[200, 200])
    lab_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(lab_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("AI Dye Recipe Recommendation", styles["Heading2"]))
    elements.append(Spacer(1, 10))
    recipe_data = [["Dye", "Amount (%)"]]
    for item in json.loads(recipe_extraction.recipe_json or "[]"):
        recipe_data.append([item.get("dye", "-"), str(item.get("percentage", item.get("amount", "-")))])
    recipe_table = Table(recipe_data, colWidths=[250, 220])
    recipe_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(recipe_table)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')}", styles["Normal"]))

    doc.build(elements)
    return pdf_path
