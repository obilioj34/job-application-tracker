"""Flask routes, form validation, and job matching."""
import hmac
import json
import os
import re
from datetime import date
from pathlib import Path
from secrets import token_hex
from urllib.parse import urlsplit

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

import database


load_dotenv(Path(__file__).with_name(".env"))
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 128 * 1024
app.teardown_appcontext(database.close_db)

STATUSES = ("Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn")
JOB_TYPES = ("Full-time", "Part-time", "Contract", "Internship")

# Each field names its MySQL column, visible label, input type, and form rules.
def field(key, label, kind="text", *, limit=0, required=False, choices=(), parent=None):
    return dict(key=key, label=label, kind=kind, limit=limit, required=required,
                choices=choices, parent=parent)


SECTIONS = {
    "companies": {
        "label": "Companies", "singular": "Company", "primary": "company_name",
        "description": "Keep track of the organizations on your radar.",
        "columns": (("company_name", "Company"), ("industry", "Industry"), ("city", "City"), ("state", "State")),
        "fields": (
            field("company_name", "Company name", limit=100, required=True),
            field("industry", "Industry", limit=50),
            field("website", "Website", "url", limit=200),
            field("city", "City", limit=50),
            field("state", "State", limit=50),
            field("notes", "Notes", "textarea", limit=4000),
        ),
    },
    "jobs": {
        "label": "Jobs", "singular": "Job", "primary": "job_title",
        "description": "Save openings, pay ranges, and the skills each role needs.",
        "columns": (("job_title", "Job title"), ("company_name", "Company"), ("job_type", "Type"), ("date_posted", "Posted")),
        "fields": (
            field("job_title", "Job title", limit=100, required=True),
            field("company_id", "Company", "relation", parent="companies", required=True),
            field("job_type", "Job type", "select", choices=JOB_TYPES),
            field("salary_min", "Minimum annual salary", "number"),
            field("salary_max", "Maximum annual salary", "number"),
            field("job_url", "Job posting URL", "url", limit=300),
            field("date_posted", "Date posted", "date"),
            field("requirements", "Required skills", "skills", limit=4000),
        ),
    },
    "applications": {
        "label": "Applications", "singular": "Application", "primary": "job_title",
        "description": "Follow each application from the day you apply to the final decision.",
        "columns": (("job_title", "Job title"), ("company_name", "Company"), ("application_date", "Applied on"), ("status", "Status")),
        "fields": (
            field("job_id", "Job", "relation", parent="jobs", required=True),
            field("application_date", "Application date", "date", required=True),
            field("status", "Status", "select", choices=STATUSES, required=True),
            field("resume_version", "Resume version", limit=50),
            field("cover_letter_sent", "Cover letter sent", "checkbox"),
            field("interview_data", "Interview details", "json", limit=6000),
        ),
    },
    "contacts": {
        "label": "Contacts", "singular": "Contact", "primary": "contact_name",
        "description": "Save the people you meet along the way.",
        "columns": (("contact_name", "Contact"), ("company_name", "Company"), ("title", "Title"), ("email", "Email")),
        "fields": (
            field("contact_name", "Contact name", limit=100, required=True),
            field("company_id", "Company", "relation", parent="companies", required=True),
            field("title", "Job title", limit=100),
            field("email", "Email", "email", limit=100),
            field("phone", "Phone", "tel", limit=20),
            field("linkedin_url", "LinkedIn URL", "url", limit=200),
            field("notes", "Notes", "textarea", limit=4000),
        ),
    },
}


@app.context_processor
def common_template_values():
    if "csrf_token" not in session:
        session["csrf_token"] = token_hex(24)
    return {"sections": SECTIONS, "csrf_token": session["csrf_token"],
            "choice_pairs": lambda choices: zip(choices, choices)}


@app.before_request
def protect_forms():
    if request.method == "POST":
        submitted = request.form.get("csrf_token", "")
        expected = session.get("csrf_token", "")
        if not expected or not hmac.compare_digest(submitted.encode(), expected.encode()):
            abort(400, "This form has expired. Return to the page and try again.")


def get_section(section):
    if section not in SECTIONS:
        abort(404)
    return SECTIONS[section]


def get_record_or_404(section, record_id):
    get_section(section)
    record = database.get_record(section, record_id)
    if record is None:
        abort(404)
    return record


def json_value(value):
    if isinstance(value, (str, bytes, bytearray)):
        return json.loads(value)
    return value


def skill_key(skill):
    return " ".join(skill.split()).casefold()


def unique_skills(skills):
    result = {}
    for skill in skills:
        if isinstance(skill, str) and skill_key(skill):
            result.setdefault(skill_key(skill), " ".join(skill.split()))
    return result


def parse_skills(text):
    return unique_skills(re.split(r"[,\n]", text))


def required_skills(requirements):
    data = json_value(requirements)
    if isinstance(data, dict):
        data = data.get("required_skills", data.get("skills", []))
    return unique_skills(data) if isinstance(data, list) else {}


def rank_jobs(jobs, user_skills):
    results = []
    for job in jobs:
        required = required_skills(job["requirements"])
        matched = [label for key, label in required.items() if key in user_skills]
        missing = [label for key, label in required.items() if key not in user_skills]
        score = len(matched) / len(required) if required else None
        results.append(dict(job=job, matched=matched, missing=missing, total=len(required),
                            score=score, percent=round(100 * score) if score is not None else None))
    return sorted(results, key=lambda result: (
        result["score"] is None, -(result["score"] or 0),
        result["job"]["job_title"].casefold(), result["job"]["job_id"],
    ))


def field_options(section):
    options = {}
    for item in SECTIONS[section]["fields"]:
        parent = item["parent"]
        if parent:
            labels = []
            for record in database.list_records(parent):
                label = record[SECTIONS[parent]["primary"]]
                if parent == "jobs":
                    label = f"{label} — {record['company_name']}"
                labels.append((str(record[database.IDS[parent]]), label))
            options[item["key"]] = dict(labels)
    return options


def convert_field(item, raw, options, record):
    kind, label, key = item["kind"], item["label"], item["key"]
    if kind == "checkbox":
        return raw == "1"
    if item["required"] and not raw:
        raise ValueError(f"{label} is required.")
    if item["limit"] and len(raw) > item["limit"]:
        raise ValueError(f"{label} must be {item['limit']} characters or fewer.")
    if kind == "skills":
        # Keep any other JSON properties saved during earlier course assignments.
        previous = json_value(record.get(key)) if record else None
        data = dict(previous) if isinstance(previous, dict) else {}
        data.pop("skills", None)
        data["required_skills"] = list(parse_skills(raw).values())
        return json.dumps(data)
    if not raw:
        return None
    if kind == "relation":
        if raw not in options[key]:
            raise ValueError(f"Choose an existing {label.lower()}.")
        return int(raw)
    if kind == "select" and raw not in item["choices"]:
        raise ValueError(f"Choose a valid {label.lower()}.")
    if kind == "date":
        try:
            value = date.fromisoformat(raw)
            if value.isoformat() != raw or value.year < 1000:
                raise ValueError
            return value
        except ValueError:
            raise ValueError(f"Enter a valid {label.lower()} as YYYY-MM-DD.") from None
    if kind == "number":
        if not re.fullmatch(r"[0-9]{1,10}", raw) or int(raw) > 2147483647:
            raise ValueError(f"{label} must be a whole number between 0 and 2,147,483,647.")
        return int(raw)
    if kind == "url":
        try:
            link = urlsplit(raw)
            valid = link.scheme in {"http", "https"} and link.hostname and not re.search(r"\s", raw)
        except ValueError:
            valid = False
        if not valid:
            raise ValueError(f"Enter an HTTP or HTTPS address for {label.lower()}.")
    if kind == "email" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", raw):
        raise ValueError("Enter a valid email address.")
    if kind == "json":
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError
            return json.dumps(data, allow_nan=False)
        except ValueError:
            raise ValueError("Interview details must be a valid JSON object.") from None
    return raw


def display_fields(section, record):
    values = {}
    for item in SECTIONS[section]["fields"]:
        key, kind = item["key"], item["kind"]
        value = record.get(key)
        if kind == "skills":
            value = ", ".join(required_skills(value).values())
        if kind == "json" and value is not None:
            value = json.dumps(json_value(value), indent=2, ensure_ascii=False)
        if kind == "checkbox":
            value = "1" if value else ""
        values[key] = str(value) if value is not None else ""
    return values


@app.get("/")
def dashboard():
    counts = database.fetch("""
        SELECT (SELECT COUNT(*) FROM companies) AS companies,
               (SELECT COUNT(*) FROM jobs) AS jobs,
               (SELECT COUNT(*) FROM contacts) AS contacts,
               (SELECT COUNT(*) FROM applications) AS applications
    """)[0]
    by_status = dict.fromkeys(STATUSES, 0)
    for row in database.fetch("SELECT status, COUNT(*) AS total FROM applications GROUP BY status"):
        by_status[row["status"]] = row["total"]
    recent = database.list_records("applications")[:5]
    return render_template("dashboard.html", counts=counts, by_status=by_status, recent=recent)


@app.get("/<section>")
def record_list(section):
    get_section(section)
    return render_template(f"{section}.html", section=section, records=database.list_records(section),
                           meta=SECTIONS[section], id_key=database.IDS[section])


@app.get("/<section>/<int:record_id>")
def record_detail(section, record_id):
    record = get_record_or_404(section, record_id)
    return render_template("detail.html", section=section, meta=SECTIONS[section],
                           record_id=record_id, values=display_fields(section, record),
                           options=field_options(section))


@app.route("/<section>/new", methods=["GET", "POST"])
@app.route("/<section>/<int:record_id>/edit", methods=["GET", "POST"])
def record_form(section, record_id=None):
    meta = get_section(section)
    record = get_record_or_404(section, record_id) if record_id is not None else None
    options = field_options(section)
    values = display_fields(section, record or {})
    if section == "applications" and record is None:
        values.update(application_date=date.today().isoformat(), status="Applied")
    errors = {}
    if request.method == "POST":
        cleaned = {}
        for item in meta["fields"]:
            key = item["key"]
            values[key] = request.form.get(key, "").strip()
            try:
                cleaned[key] = convert_field(item, values[key], options, record)
            except ValueError as error:
                errors[key] = str(error)
        low, high = cleaned.get("salary_min"), cleaned.get("salary_max")
        if low is not None and high is not None and low > high:
            errors["salary_max"] = "Maximum salary must be at least the minimum salary."
        if not errors:
            try:
                if record_id is None:
                    record_id = database.insert_record(section, cleaned)
                else:
                    database.update_record(section, record_id, cleaned)
            except mysql.connector.IntegrityError as error:
                if error.errno != 1452:
                    raise
                errors["form"] = "A selected record was removed. Choose another option."
                options = field_options(section)
            else:
                flash(f"{meta['singular']} saved.", "success")
                return redirect(url_for("record_detail", section=section, record_id=record_id))
    return render_template("form.html", section=section, meta=meta, record_id=record_id,
                           values=values, options=options, errors=errors), 422 if errors else 200


@app.route("/<section>/<int:record_id>/delete", methods=["GET", "POST"])
def record_delete(section, record_id):
    record = get_record_or_404(section, record_id)
    meta = SECTIONS[section]
    error = None
    if request.method == "POST":
        try:
            database.delete_record(section, record_id)
        except mysql.connector.IntegrityError as exc:
            if exc.errno != 1451:
                raise
            error = "Remove or reassign the jobs and contacts linked to this company first."
            if section == "jobs":
                error = "Remove or reassign the applications linked to this job first."
        else:
            flash(f"{meta['singular']} deleted.", "success")
            return redirect(url_for("record_list", section=section))
    return render_template("delete.html", section=section, meta=meta, record_id=record_id,
                           name=record.get(meta["primary"]), error=error), 409 if error else 200


@app.route("/job-match", methods=["GET", "POST"])
def job_match():
    skills = request.form.get("skills", "").strip()
    results = None
    error = None
    if request.method == "POST":
        if len(skills) > 4000:
            error = "Use 4,000 characters or fewer."
        elif not parse_skills(skills):
            error = "Enter at least one skill."
        else:
            results = rank_jobs(database.list_records("jobs"), parse_skills(skills))
    return render_template("job_match.html", skills=skills, results=results,
                           error=error), 422 if error else 200


if __name__ == "__main__":
    app.run()
