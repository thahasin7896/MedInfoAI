import re
from pathlib import Path

import pymupdf


def process_report(file_path):
    """
    Extract text from an uploaded PDF medical report.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        return {
            "status": "error",
            "message": "Report file not found."
        }

    if file_path.suffix.lower() != ".pdf":
        return {
            "status": "error",
            "message": "Currently, PDF processing is supported."
        }

    try:
        document = pymupdf.open(str(file_path))

        pages = []

        for page in document:
            text = page.get_text()
            pages.append(text)

        document.close()

        extracted_text = "\n".join(pages).strip()

        return {
            "status": "success",
            "filename": file_path.name,
            "source": "EXTRACTED FROM UPLOADED REPORT",
            "text": extracted_text
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)
        }


def prepare_for_structuring(extracted_text):
    """
    Prepare extracted report text for structured medical information extraction.
    """

    if not extracted_text:
        return {
            "status": "empty",
            "message": "No text could be extracted from the report."
        }

    return {
        "status": "ready",
        "text": extracted_text,
        "provenance": "EXTRACTED FROM UPLOADED REPORT"
    }


def create_structured_result(
    report_id,
    test_name,
    value=None,
    unit=None,
    reference_range=None,
    result_status=None,
    observation=None
):
    """
    Create a structured medical result.

    Reference ranges must come from the source report.
    """

    return {
        "report_id": report_id,
        "test_name": test_name,
        "value": value,
        "unit": unit,
        "reference_range": reference_range,
        "result_status": result_status,
        "observation": observation,
        "provenance": "EXTRACTED FROM UPLOADED REPORT",
        "verified": 0
    }


def extract_structured_results(text, report_id):
    """
    Extract common lab-result patterns from report text.

    Reference ranges are used only when present in the source text.
    """

    results = []

    if not text:
        return results

    lines = text.splitlines()

    for line in lines:
        line = line.strip()

        if not line:
            continue

        # Example:
        # Hemoglobin 13.5 g/dL 12-16 g/dL
        #
        # Also supports:
        # Hemoglobin 13.5 g/dL
        # Glucose 95 mg/dL 70-100 mg/dL

        pattern = (
            r"^([A-Za-z][A-Za-z0-9 /().-]{2,40})\s+"
            r"([0-9]+(?:\.[0-9]+)?)"
            r"(?:\s+([A-Za-z/%µμ]+(?:/[A-Za-z]+)?))?"
            r"(?:\s+([0-9]+(?:\.[0-9]+)?\s*[-–]\s*[0-9]+(?:\.[0-9]+)?))?"
            r"(?:\s+([A-Za-z/%µμ]+(?:/[A-Za-z]+)?))?$"
        )

        match = re.search(pattern, line)

        if not match:
            continue

        test_name = match.group(1).strip()
        value = match.group(2)
        unit = match.group(3) or ""
        reference_range = match.group(4) or ""

        result_status = "UNKNOWN"

        if reference_range:
            numbers = re.findall(
                r"[0-9]+(?:\.[0-9]+)?",
                reference_range
            )

            if len(numbers) >= 2:
                low = float(numbers[0])
                high = float(numbers[1])
                numeric_value = float(value)

                if numeric_value < low:
                    result_status = "LOW"

                elif numeric_value > high:
                    result_status = "HIGH"

                else:
                    result_status = "NORMAL"

        results.append(
            create_structured_result(
                report_id=report_id,
                test_name=test_name,
                value=value,
                unit=unit,
                reference_range=(
                    reference_range
                    if reference_range
                    else "Reference range unavailable"
                ),
                result_status=result_status,
                observation="Extracted from uploaded report."
            )
        )

    return results