-- Run once after schema.sql on a fresh database. All records are fictional.
USE job_tracker;
START TRANSACTION;

INSERT INTO companies (company_name, industry, website, city, state, notes)
VALUES ('TechCorp', 'Software', 'https://example.com/techcorp', 'Miami', 'FL', 'Makes tools for small businesses.');
SET @techcorp = LAST_INSERT_ID();

INSERT INTO companies (company_name, industry, city, state, notes)
VALUES ('DataCo', 'Analytics', 'Fort Lauderdale', 'FL', 'Analytics and reporting consultancy.');
SET @dataco = LAST_INSERT_ID();

INSERT INTO companies (company_name, industry, city, state)
VALUES ('Harbor Studio', 'Design', 'Miami', 'FL');
SET @harbor = LAST_INSERT_ID();

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, date_posted, requirements)
VALUES (@techcorp, 'Software Developer', 'Full-time', 72000, 95000, CURRENT_DATE - INTERVAL 10 DAY,
        JSON_OBJECT('required_skills', JSON_ARRAY('Python', 'SQL', 'Flask')));
SET @developer = LAST_INSERT_ID();

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, date_posted, requirements)
VALUES (@dataco, 'Data Analyst', 'Full-time', 64000, 82000, CURRENT_DATE - INTERVAL 8 DAY,
        JSON_OBJECT('required_skills', JSON_ARRAY('Python', 'SQL', 'Tableau')));
SET @analyst = LAST_INSERT_ID();

INSERT INTO jobs (company_id, job_title, job_type, date_posted, requirements)
VALUES (@harbor, 'Web Design Intern', 'Internship', CURRENT_DATE - INTERVAL 3 DAY,
        JSON_OBJECT('required_skills', JSON_ARRAY('HTML', 'CSS', 'Figma')));

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data)
VALUES
    (@developer, CURRENT_DATE - INTERVAL 6 DAY, 'Interview', 'Developer v2', TRUE,
     JSON_OBJECT('round', 'Phone screen', 'notes', 'Review Flask routes and SQL joins.')),
    (@analyst, CURRENT_DATE - INTERVAL 2 DAY, 'Screening', 'Analytics v1', FALSE, NULL),
    (@developer, CURRENT_DATE - INTERVAL 24 DAY, 'Applied', 'Developer v1', FALSE, NULL);

INSERT INTO contacts (company_id, contact_name, title, email, notes)
VALUES (@techcorp, 'Jordan Lee', 'Recruiter', 'jordan@example.com', 'Ask about the interview format.'),
       (@dataco, 'Casey Morgan', 'Analytics Lead', 'casey@example.com', 'Met at a campus career fair.');
COMMIT;
