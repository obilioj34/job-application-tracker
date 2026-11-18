# Job Application Tracker

A local Flask app for tracking companies, jobs, applications, and professional contacts. It stores records in MySQL and compares your skills with the requirements of saved jobs.

## Setup from a fresh clone

You need Python 3.10 or later, Git, and a running MySQL 8.x server. Install [MySQL Community Server](https://dev.mysql.com/downloads/mysql/8.4.html) if you do not have it. The MySQL command-line client must be on your PATH to use the `mysql` commands below.

1. Clone this repository.

   ```sh
   git clone https://github.com/obilioj34/job-application-tracker.git
   cd job-application-tracker
   ```

2. Create a virtual environment and install the dependencies.

   **Windows PowerShell**

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

   **macOS or Linux**

   ```sh
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   cp .env.example .env
   ```

3. From the repository folder, connect to MySQL as an administrator.

   ```sh
   mysql -u root -p
   ```

   Then run these commands in the MySQL prompt. Replace the example password and use the same value in `.env`. The sample data is optional. Load it once on a fresh database for the example jobs and applications.

   ```sql
   SOURCE schema.sql
   SOURCE sample_data.sql
   CREATE USER 'job_tracker_app'@'localhost' IDENTIFIED BY 'replace-with-your-local-password';
   GRANT SELECT, INSERT, UPDATE, DELETE ON job_tracker.* TO 'job_tracker_app'@'localhost';
   EXIT
   ```

   If the account already exists, use its password or update it with `ALTER USER`. Edit your local `.env` if MySQL uses another port or username. The app reads `.env` from the repository folder.

4. Run Flask and open [the local dashboard](http://127.0.0.1:5000).

   ```powershell
   # Windows PowerShell
   .\.venv\Scripts\python.exe app.py
   ```

   ```sh
   # macOS or Linux
   .venv/bin/python app.py
   ```

   If port 5000 is in use, start Flask with `python -m flask --app app run --port 5001` using your virtual environment's Python. If you see a MySQL connection error, check that the server is running and verify the host, port, username, and password in `.env`.

## How to use it

- Add a company first. Jobs and contacts belong to a company.
- Add a job, then use Applications to track when you applied, the status, and any interview notes.
- Click a record's name to view all its fields. Edit from the detail or list page, or open the delete confirmation. MySQL protects companies and jobs that still have linked records.
- Try **Job Match** with `Python, SQL, Flask`. With the sample data, Software Developer gets **100%** and Data Analyst gets **67%**, with Tableau listed as missing.

Job Match divides the number of matched skills by the number of unique required skills. It compares whole skill names after trimming spaces and ignoring case. Jobs without listed requirements appear after the scored jobs. The calculation runs in Python, and the skills entered on the match page are used for that request.

## Project files

- `app.py` defines the Flask pages, validates form data, and calculates matches.
- `database.py` connects to MySQL, runs queries, and commits writes.
- `templates/` and `static/style.css` contain the HTML and CSS.
- `schema.sql` creates the database and its four tables. `sample_data.sql` adds fictional records.
- `AI_USAGE.md` documents the use of ChatGPT.
- `demo.mp4` shows the browser, Flask server, and MySQL working together.

## Verification

Run `python -m unittest discover -s tests -v` with the same Python and MySQL settings used to run the application. The integration test creates temporary records and deletes them afterward. Run it against a development or test database. It checks create, list, detail, edit, and delete for all four tables, input validation, foreign-key delete protection, and Job Match.
