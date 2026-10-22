**## 1. What did I use an AI assistant for, and what did I do myself?**

I used ChatGPT to troubleshoot the Windows PowerShell commands.

I independently created the MongoDB document and memory features, ran the PowerShell commands, installed and started MongoDB, operated MongoDB Compass, tested the FastAPI endpoints, sent the required API requests, captured screenshots, and interpreted the results.

**## 2. What AI-produced output was wrong or unsuitable?**

One initially suggested command assumed that the terminal was already using the project directory and virtual environment. When I ran the command from a different PowerShell location, the required project files and dependencies were not found. MongoDB commands also failed while the MongoDB service was not running.

**## 3. How did I detect the problem or verify the result?**

I detected the issue from the PowerShell prompt and the command errors. The prompt showed that I was outside the repository, and the MongoDB connection test could not reach 127.0.0.1:27017. I verified the environment by explicitly changing to the repository, using the project’s .venv Python executable, checking the MongoDB service, and testing the port.

**## 4. What did I change, and why does it work now?**

I changed the procedure to use the full repository path, run commands through .\.venv\Scripts\python.exe, start MongoDB before launching the backend, and use a separate terminal for verification. This works because the commands now run from the correct project directory, use the intended Python environment, and connect to an active MongoDB service. I confirmed the result with the successful API tests, MongoDB connection, and final verification output.