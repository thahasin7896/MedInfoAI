from pathlib import Path
import re
import uuid


def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF using PyMuPDF.
    Returns an empty string if extraction is not possible.
    """
    try:
        import fitz

        document = fitz.open(file_path)
        pages = []

        for page in document:
            pages.append(page.get_text("text"))

        document.close()

        return "\n".join(pages)

    except Exception:
        return ""


def extract_structured_results(text):
    """
    Basic laboratory-result extraction.
    This is intentionally lightweight so it works reliably on Vercel.
    """

    results = []

    if not text:
        return results

    patterns = [
        (
            "Hemoglobin",
            r"hemoglobin\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
            "g/dL",
            "12.0 - 15.5"
        ),
        (
            "Glucose",
            r"(?:glucose|blood sugar)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
            "mg/dL",
            "70 - 100"
        ),
        (
            "Creatinine",
            r"creatinine\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
            "mg/dL",
            "0.6 - 1.1"
        ),
        (
            "Cholesterol",
            r"cholesterol\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
            "mg/dL",
            "125 - 200"
        ),
        (
            "Platelets",
            r"platelets?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
            "10^3/uL",
            "150 - 450"
        ),
    ]

    for parameter, pattern, unit, reference in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if not match:
            continue

        value = float(match.group(1))

        if parameter == "Glucose":
            status = "HIGH" if value > 100 else "NORMAL"
        elif parameter == "Hemoglobin":
            status = "LOW" if value < 12 else "NORMAL"
        elif parameter == "Creatinine":
            status = "HIGH" if value > 1.1 else "NORMAL"
        elif parameter == "Cholesterol":
            status = "HIGH" if value > 200 else "NORMAL"
        elif parameter == "Platelets":
            status = (
                "LOW" if value < 150
                else "HIGH" if value > 450
                else "NORMAL"
            )
        else:
            status = "NORMAL"

        results.append({
            "id": str(uuid.uuid4()),
            "parameter": parameter,
            "result": str(value).rstrip("0").rstrip("."),
            "unit": unit,
            "reference_range": reference,
            "status": status,
            "confidence": 90,
            "provenance": "Uploaded Report",
            "verification_status": "Needs Review",
            "source_page": 1
        })

    return results


def process_report(file_path):
    """
    Process an uploaded medical report.
    """

    path = Path(file_path)

    result = {
        "filename": path.name,
        "success": True,
        "text_extracted": False,
        "lab_results": [],
        "message": ""
    }

    if path.suffix.lower() == ".pdf":
        text = extract_text_from_pdf(str(path))

        if text.strip():
            result["text_extracted"] = True
            result["lab_results"] = extract_structured_results(text)
            result["message"] = "PDF processed successfully."
        else:
            result["message"] = (
                "PDF received. No machine-readable text was found."
            )

    else:
        result["message"] = (
            "Image received. Basic upload completed. "
            "OCR processing is not enabled in this lightweight deployment."
        )

    return result