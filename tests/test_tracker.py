"""End-to-end form and database checks. Run against a development MySQL database."""
import json
import unittest
from uuid import uuid4

from app import app, parse_skills, rank_jobs
import database


class JobMatchTests(unittest.TestCase):
    def test_rank_with_case_duplicates_and_unscored_jobs(self):
        jobs = [
            dict(job_id=1, job_title="Analyst", requirements='{"required_skills":["Python","SQL","Tableau"]}'),
            dict(job_id=2, job_title="Developer", requirements='{"skills":["Python","SQL","Flask"," SQL "]}'),
            dict(job_id=3, job_title="Unscored", requirements=None),
            dict(job_id=4, job_title="Design", requirements='["Figma"]'),
        ]
        results = rank_jobs(jobs, parse_skills(" PYTHON, sql, SQL\nFlask"))
        self.assertEqual([result["percent"] for result in results], [100, 67, 0, None])
        self.assertEqual(results[1]["missing"], ["Tableau"])


class TrackerIntegrationTests(unittest.TestCase):
    def test_all_sections_and_matching(self):
        app.config["TESTING"] = True
        self.addCleanup(app.config.update, TESTING=False)
        client = app.test_client()
        name = "Tracker test " + uuid4().hex[:8]
        self.assertEqual(client.get("/").status_code, 200)
        with client.get("/static/style.css") as stylesheet:
            self.assertEqual(stylesheet.status_code, 200)
        self.assertEqual(client.get("/absent").status_code, 404)
        self.assertEqual(client.post("/companies/new", data={"company_name": name}).status_code, 400)

        with client.session_transaction() as session:
            token = session["csrf_token"]

        def post(url, **fields):
            return client.post(url, data={"csrf_token": token, **fields})

        def add(section, **fields):
            response = post(f"/{section}/new", **fields)
            self.assertEqual(response.status_code, 302, response.get_data(as_text=True))
            location = response.headers["Location"]
            record_id = int(location.rsplit("/", 1)[-1])
            self.addCleanup(self.remove_record, section, record_id)
            self.assertEqual(client.get(location).status_code, 200)
            self.assertIn(location.encode(), client.get(f"/{section}").data)
            self.assertEqual(client.get(location + "/edit").status_code, 200)
            return location, record_id

        self.assertEqual(post("/companies/new", company_name="  ").status_code, 422)
        company, company_id = add("companies", company_name=name, city="Miami")
        self.assertEqual(post(company + "/edit", company_name=name, city="Orlando").status_code, 302)
        self.assertIn(b"Orlando", client.get(company).data)

        self.assertEqual(post("/jobs/new", job_title=name, company_id="0").status_code, 422)
        self.assertEqual(post("/jobs/new", job_title=name, company_id=company_id,
                              salary_min=10000, salary_max=1).status_code, 422)
        job, job_id = add("jobs", job_title=name, company_id=company_id, job_type="Internship",
                          requirements="Python, SQL", salary_min=15000, salary_max=20000)
        with app.app_context():
            database.write("UPDATE jobs SET requirements = %s WHERE job_id = %s",
                           ('{"required_skills":["Python","SQL"],"experience_years":2}', job_id))
        self.assertEqual(post(job + "/edit", job_title=name, company_id=company_id,
                              requirements="Python, SQL, Flask").status_code, 302)
        with app.app_context():
            saved = database.get_record("jobs", job_id)
            self.assertEqual(json.loads(saved["requirements"])["experience_years"], 2)
        self.assertIn(b"Python, SQL, Flask", client.get(job).data)

        self.assertEqual(post("/applications/new", job_id=job_id, status="Applied",
                              application_date="2026-02-31").status_code, 422)
        self.assertEqual(post("/applications/new", job_id=job_id, status="Applied",
                              application_date="2026-11-18", interview_data="[]").status_code, 422)
        application, _ = add("applications", job_id=job_id, application_date="2026-11-18",
                             status="Applied", cover_letter_sent="1", interview_data='{"round":1}')
        self.assertEqual(post(application + "/edit", job_id=job_id, application_date="2026-11-18",
                              status="Offer", cover_letter_sent="1").status_code, 302)
        self.assertIn(b"Offer", client.get(application).data)

        self.assertEqual(post("/contacts/new", company_id=company_id, contact_name=name,
                              email="bad-email").status_code, 422)
        contact, _ = add("contacts", company_id=company_id, contact_name=name, email="test@example.com")
        self.assertEqual(post(contact + "/edit", company_id=company_id, contact_name=name,
                              phone="305-555-0100").status_code, 302)
        self.assertIn(b"305-555-0100", client.get(contact).data)

        self.assertEqual(client.get("/job-match").status_code, 200)
        self.assertEqual(post("/job-match", skills=", ,").status_code, 422)
        match = post("/job-match", skills=" PYTHON, sql, SQL ")
        self.assertEqual(match.status_code, 200)
        self.assertIn(f'href="{job}"'.encode(), match.data)
        self.assertIn(b"67%", match.data)
        self.assertIn(b"<strong>Missing</strong> Flask", match.data)

        self.assertEqual(post(company + "/delete").status_code, 409)
        self.assertEqual(post(job + "/delete").status_code, 409)
        for location in (application, contact, job, company):
            self.assertEqual(client.get(location + "/delete").status_code, 200)
            self.assertEqual(client.get(location).status_code, 200)
            self.assertEqual(post(location + "/delete").status_code, 302)
            self.assertEqual(client.get(location).status_code, 404)

    @staticmethod
    def remove_record(section, record_id):
        with app.app_context():
            database.delete_record(section, record_id)
