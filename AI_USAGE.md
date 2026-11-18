# AI Usage Documentation

## Tools used

I used ChatGPT through Codex to help build the Job Application Tracker. I provided the project specification, rubric, and an example dashboard. ChatGPT drafted the initial application and assisted with testing and documentation.

## Key prompts

- “help me with my school project as If I was doing it”
- “Build a complete web application that helps users track their job applications. You will use MySQL for the database, Python with Flask for the backend, and HTML/CSS for the frontend.”
- I also asked for CRUD on all four tables, a skill match feature, thorough testing, and setup instructions for someone who clones the GitHub repository.

## What worked well

ChatGPT organized the SQL schema around the four tables in the specification and used foreign keys to connect them. It drafted Flask routes, a shared layout for the list and form pages, and MySQL queries that use placeholders for values. It also drafted the skill comparison and used the sample jobs from the specification to check the 100% and 67% results.

## What changed during development

During the AI-assisted implementation, ChatGPT checked the earlier coursework and used its `required_skills` JSON key. It also made the job edit form preserve other properties in the requirements object, added server-side validation for salary ranges and JSON input, and made linked records block parent deletion. These changes were part of the AI-assisted implementation.

## Lessons from the project

The form and the database check different things. Flask can explain an invalid salary or a missing field, while a MySQL foreign key prevents an application from referencing a job that does not exist. A small set of requirements with known answers made it possible to verify the matching formula. Testing with `python, SQL, sql, Flask` also checks that case and duplicate skills do not inflate the score.
