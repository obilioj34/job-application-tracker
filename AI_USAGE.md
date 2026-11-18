# AI Usage Documentation

## Tools used

I used ChatGPT through Codex to help build the Job Application Tracker. I provided the project specification, rubric, and an example dashboard. ChatGPT drafted the initial application and assisted with testing and documentation.

## Key prompts

“Using my course specification, write a MySQL schema for companies, jobs, applications, and contacts. Include the foreign keys and the JSON columns for job requirements and interview details.”
“Help me build Flask routes to add, list, view, edit, and delete records in all four tables. Show me how to validate the forms and ask for confirmation before deleting a record.”
“Help me build the dashboard and HTML templates. Show application counts by status, and use the same layout and navigation across the pages.”
“Write a Python function that compares the skills I enter with each job’s required_skills list. Ignore capitalization and duplicates, rank jobs by percentage, and show which skills are missing.”
“Help me test the app from a fresh clone using MySQL. Check all four CRUD sections, invalid form inputs, and the expected 100% and 67% Job Match results. Write setup instructions my instructor can follow.”

## What worked well

ChatGPT organized the SQL schema around the four tables in the specification and used foreign keys to connect them. It drafted Flask routes, a shared layout for the list and form pages, and MySQL queries that use placeholders for values. It also drafted the skill comparison and used the sample jobs from the specification to check the 100% and 67% results.

## What changed during development

During the AI-assisted implementation, ChatGPT checked the earlier coursework and used its `required_skills` JSON key. It also made the job edit form preserve other properties in the requirements object, added server-side validation for salary ranges and JSON input, and made linked records block parent deletion. These changes were part of the AI-assisted implementation.

## Lessons from the project

The form and the database check different things. Flask can explain an invalid salary or a missing field, while a MySQL foreign key prevents an application from referencing a job that does not exist. A small set of requirements with known answers made it possible to verify the matching formula. Testing with `python, SQL, sql, Flask` also checks that case and duplicate skills do not inflate the score.
