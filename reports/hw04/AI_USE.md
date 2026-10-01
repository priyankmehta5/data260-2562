    # HW4 AI Use Disclosure

## 1. What did I use an AI assistant for, and what did I do myself?

I used ChatGPT to troubleshoot environment setup and installation issues, including outdated Node.js and npm versions, missing Python packages, MySQL command availability, and PowerShell command errors.

I independently implemented and tested the React frontend, FastAPI backend, MySQL database, session-based authentication, CRUD operations, N+1 experiment, RAG configurations, evaluation, and verification script.

## 2. What AI-produced output was wrong or unsuitable?

An initially suggested command used the system Python installation instead of the project’s virtual environment. When I ran the database seed script, it failed with `ModuleNotFoundError: No module named 'sqlalchemy'`, even though SQLAlchemy was required by the backend.

## 3. How did I detect the problem or verify the result?

I detected the issue from the PowerShell prompt and traceback. The prompt did not show `(.venv)`, and Python reported that the `sqlalchemy` package was unavailable. This confirmed that the command was running outside the configured project environment.

## 4. What did I change, and why does it work now?

I activated the project virtual environment before running the installation and seed commands. I then installed the required packages from `requirements.txt` and reran the database seed script. It worked because Python used the project environment containing SQLAlchemy and the other backend dependencies. I verified the result by confirming that MySQL contained 5,000 incident records and 200 incident-note records.