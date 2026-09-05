import re
from pathlib import Path


def extract_text_from_pdf(file_path):
    """Extract text from a PDF."""
    try:
        import fitz

        document = fitz.open(str(file_path))
        return "\n".join(page.get_text() for page in document)
    except Exception:
        return ""


def extract_structured_results(text):
    """Extract basic laboratory results."""
    if not text:
        return []

    patterns = [
        ("Hemoglobin", r"hemoglobin\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
         "g/dL", "12.0 - 15.5"),
        ("Glucose", r"(?:glucose|blood sugar)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
         "mg/dL", "70 - 100"),
        ("Creatinine", r"creatinine\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
         "mg/dL", "0.6 - 1.1"),
        ("Cholesterol", r"cholesterol\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
         "mg/dL", "125 - 200"),
        ("Platelets", r"platelets?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
         "10^3/uL", "150 - 450"),
    ]

    results = []

    for parameter, pattern, unit, reference in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            value = float(match.group(1))
            results.append({
                "parameter": parameter,
                "title": parameter,
                "result": str(value),
                "value": str(value),
                "unit": unit,
                "reference_range": reference,
                "status": "Needs Review",
                "provenance": "Uploaded Report",
            })

    return results


def process_report(file_path):
    """Process an uploaded medical report."""
    path = Path(file_path)

    if path.suffix.lower() == ".pdf":
        text = extract_text_from_pdf(path)
    else:
        text = ""

    return {
        "filename": path.name,
        "text": text,
        "lab_results": extract_structured_results(text),
        "status": "Processed",
    }