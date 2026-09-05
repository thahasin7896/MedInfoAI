from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from database.db import get_connection, initialize_database
from services.report_processor import extract_structured_results, process_report


app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

initialize_database()


@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/patient")
def patient():
    return render_template("patient.html")


@app.route("/patient/save", methods=["POST"])
def save_patient():
    connection = get_connection()

    connection.execute("""
        INSERT INTO patients (
            full_name, dob, age, sex, patient_id, contact,
            symptoms, conditions, allergies, medications,
            surgeries, family_history, lifestyle, other_info
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        request.form.get("full_name"),
        request.form.get("dob"),
        request.form.get("age"),
        request.form.get("sex"),
        request.form.get("patient_id"),
        request.form.get("contact"),
        request.form.get("symptoms"),
        request.form.get("conditions"),
        request.form.get("allergies"),
        request.form.get("medications"),
        request.form.get("surgeries"),
        request.form.get("family_history"),
        request.form.get("lifestyle"),
        request.form.get("other_info"),
    ))

    connection.commit()
    connection.close()

    return redirect(url_for("patients"))


@app.route("/patients")
def patients():
    connection = get_connection()
    patient_list = connection.execute("""
        SELECT *
        FROM patients
        ORDER BY created_at DESC
    """).fetchall()
    connection.close()

    return render_template("patients.html", patients=patient_list)


@app.route("/reports")
def reports():
    connection = get_connection()
    report_list = connection.execute("""
        SELECT *
        FROM reports
        ORDER BY uploaded_at DESC
    """).fetchall()
    connection.close()

    return render_template("reports.html", reports=report_list)


@app.route("/reports/upload", methods=["POST"])
def upload_report():
    file = request.files.get("file") or request.files.get("report")

    if not file or not file.filename:
        return "No report selected.", 400

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return "Unsupported file type.", 400

    filename = secure_filename(file.filename)
    file_path = UPLOAD_FOLDER / filename
    file.save(file_path)

    result = process_report(file_path)

    connection = get_connection()
    cursor = connection.execute("""
        INSERT INTO reports (
            filename,
            extracted_text,
            processing_status
        )
        VALUES (?, ?, ?)
    """, (
        filename,
        result.get("text", ""),
        result.get("status", "uploaded"),
    ))

    report_id = cursor.lastrowid
    connection.commit()
    connection.close()

    structured_results = extract_structured_results(
        result.get("text", ""),
        report_id,
    )

    connection = get_connection()

    for item in structured_results:
        connection.execute("""
            INSERT INTO medical_results (
                report_id,
                test_name,
                value,
                unit,
                reference_range,
                result_status,
                observation,
                provenance,
                verified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.get("report_id", report_id),
            item.get("test_name", ""),
            item.get("value", ""),
            item.get("unit", ""),
            item.get("reference_range", ""),
            item.get("result_status", ""),
            item.get("observation", ""),
            item.get("provenance", ""),
            item.get("verified", False),
        ))

    connection.commit()
    connection.close()

    return redirect(url_for("results"))

@app.route("/results/verify/<int:result_id>", methods=["POST"])
def verify_result(result_id):
    connection = get_connection()

    connection.execute("""
        UPDATE medical_results
        SET verified = 1
        WHERE id = ?
    """, (result_id,))

    connection.commit()
    connection.close()

    return redirect(url_for("results"))
@app.route("/timeline")
def timeline():
    connection = get_connection()

    events = connection.execute("""
        SELECT 'Medical Report Uploaded' AS event,
               filename AS details,
               uploaded_at AS event_time
        FROM reports

        UNION ALL

        SELECT 'Medical Result Extracted' AS event,
               test_name AS details,
               created_at AS event_time
        FROM medical_results

        UNION ALL

        SELECT 'Patient Information Added' AS event,
               full_name AS details,
               created_at AS event_time
        FROM patients

        ORDER BY event_time DESC
    """).fetchall()

    connection.close()

    return render_template("timeline.html", events=events)
@app.route("/conflicts")
def conflicts():
    connection = get_connection()

    results = connection.execute("""
        SELECT test_name, value, result_status,
               reference_range, created_at
        FROM medical_results
        ORDER BY test_name, created_at ASC
    """).fetchall()

    connection.close()

    conflicts_found = []

    previous = {}

    for result in results:
        test_name = result["test_name"]

        if test_name in previous:
            old_value = previous[test_name]["value"]

            if old_value != result["value"]:
                conflicts_found.append({
                    "test_name": test_name,
                    "previous_value": old_value,
                    "current_value": result["value"],
                    "message": "Different values were recorded in different reports. Please review the source reports."
                })

        previous[test_name] = result

    return render_template(
        "conflicts.html",
        conflicts=conflicts_found
    )
@app.route("/analytics")
def analytics():
    connection = get_connection()

    results = connection.execute("""
        SELECT test_name, value, result_status, created_at
        FROM medical_results
        ORDER BY created_at ASC
    """).fetchall()

    connection.close()

    return render_template("analytics.html", results=results)
@app.route("/summary")
def summary():
    connection = get_connection()

    results = connection.execute("""
        SELECT test_name, value, unit, reference_range,
               result_status, observation, provenance, verified
        FROM medical_results
        ORDER BY created_at DESC
    """).fetchall()

    connection.close()

    return render_template("summary.html", results=results)
@app.route("/results")
def results():
    connection = get_connection()
    result_list = connection.execute("""
        SELECT *
        FROM medical_results
        ORDER BY created_at DESC
    """).fetchall()
    connection.close()

    return render_template("results.html", results=result_list)


if __name__ == "__main__":
    app.run(debug=True)