HOMEWORK 2 REPRODUCIBLE RUN INSTRUCTIONS

Repository:
https://github.com/priyankmehta5/data260-2562

Student configuration:
SID4: 2562
PORT_BASE: 8762
SEED: 2562
VERIFY_SEED: 262562
Domain: Municipal Transit Incidents
Model: qwen3:1.7b
Temperature: 0.0

1. CLONE THE REPOSITORY

git clone https://github.com/priyankmehta5/data260-2562.git
cd data260-2562

To reproduce a specific submitted version, check out its commit:

git checkout <commit-hash>

Replace <commit-hash> with the commit recorded in reports/hw02/verification.json.

2. CREATE AND ACTIVATE THE PYTHON ENVIRONMENT

Windows PowerShell:

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

3. PREPARE OLLAMA

Install Ollama if it is not already installed. Download the model:

ollama pull qwen3:1.7b

Confirm that the model is available:

ollama list

Start Ollama if it is not already running:

ollama serve

Because qwen3:8b and qwen3:4b caused VIDEO_MEMORY_MANAGEMENT_INTERNAL system errors on the development laptop, the experiments used qwen3:1.7b with CPU-only execution.

Confirm the active model and processor allocation in a separate PowerShell window:

ollama ps

4. START THE FASTAPI APPLICATION

Activate the virtual environment and run:

uvicorn code.api.main:app --host 127.0.0.1 --port 8762

Open the frontend:

http://localhost:8762

Open the FastAPI documentation:

http://localhost:8762/docs

The API should return municipal transit incident records from:

http://localhost:8762/api/incidents

Stop the server with Ctrl+C after testing.

5. RUN THE NORMAL LANGGRAPH WORKFLOW

python code/transit_graph/workflow.py --title "VTA Blue Line Signal Failure" --content "A signal failure near Santa Clara station caused major delays and disrupted Blue Line light rail service during the morning commute." --email "priyank.mehta@sjsu.edu" --model qwen3:1.7b --temperature 0.0 --strict

The output should show streamed Supervisor, Planner, and Reviewer updates. The workflow should finish instead of continuing indefinitely. The final proposal should contain exactly three tags and a summary of no more than 25 words.

6. RUN THE FORCED REVIEWER CORRECTION LOOP

python code/transit_graph/workflow.py --title "VTA Blue Line Signal Failure" --content "A signal failure near Santa Clara station caused major delays and disrupted Blue Line light rail service during the morning commute." --email "priyank.mehta@sjsu.edu" --model qwen3:1.7b --temperature 0.0 --strict --force-review-issue

The first Reviewer result should reject the proposal. The Supervisor should route execution back to the Planner. The revised proposal should be reviewed again, and the graph should finish after the final approval.

7. VERIFY THE FIXED SCHEMA INPUT

Get-Content .\reports\hw02\cases\schema_input.json | ConvertFrom-Json | Format-List

The output should display the title, content, email, and strict fields without a JSON parsing error.

8. RUN THE 30-RUN SCHEMA VALIDATION EXPERIMENT

python code/transit_graph/schema_experiment.py --input reports/hw02/cases/schema_input.json --model qwen3:1.7b --temperature 0.0 --runs 30 --turn-ceiling 10

The script saves results incrementally in:

reports/hw02/raw/schema_validation_runs.json
reports/hw02/raw/schema_validation_runs.csv
reports/hw02/raw/schema_validation_summary.json

The submitted experiment produced 30 valid first-attempt results, a 100 percent completion rate, and a mean latency of 6487.7 milliseconds.

The experiment script is resumable. If all 30 submitted runs already exist, it will reuse them instead of repeating the model calls.

9. RUN THE TURN-CEILING COMPARISON

python code/transit_graph/ceiling_experiment.py --input reports/hw02/cases/schema_input.json --model qwen3:1.7b --temperature 0.0 --runs 20

The script runs 20 trials with a ceiling of 2 and 20 trials with a ceiling of 10. It saves:

reports/hw02/raw/ceiling_comparison_runs.json
reports/hw02/raw/ceiling_comparison_runs.csv
reports/hw02/raw/ceiling_comparison_summary.json

The submitted ceiling-2 configuration completed 0 of 20 runs. The ceiling-10 configuration completed 20 of 20 runs.

The experiment script is resumable. Existing completed trials are not repeated.

10. VERIFY THE ADVERSARIAL INPUT

Get-Content .\reports\hw02\cases\adversarial_input.json | ConvertFrom-Json | Format-List

The adversarial input asks the model to violate the required output schema.

11. RUN THE FIVE ADVERSARIAL TRIALS

python code/transit_graph/adversarial_experiment.py --input reports/hw02/cases/adversarial_input.json --model qwen3:1.7b --temperature 0.0 --runs 5 --turn-ceiling 10

The script saves:

reports/hw02/raw/adversarial_runs.json
reports/hw02/raw/adversarial_summary.json

The submitted experiment produced five ceiling hits in five trials. This demonstrates that the turn ceiling stops repeated invalid responses instead of allowing an unlimited loop.

12. VERIFY THE REQUIRED RUN COUNTS

$schema = (Get-Content .\reports\hw02\raw\schema_validation_runs.json | ConvertFrom-Json).Count
$ceiling = (Get-Content .\reports\hw02\raw\ceiling_comparison_runs.json | ConvertFrom-Json).Count
$adversarial = (Get-Content .\reports\hw02\raw\adversarial_runs.json | ConvertFrom-Json).Count

[PSCustomObject]@{
    SchemaRuns = $schema
    CeilingRuns = $ceiling
    AdversarialRuns = $adversarial
    TotalRuns = $schema + $ceiling + $adversarial
} | Format-List

Expected submitted counts:

SchemaRuns: 30
CeilingRuns: 40
AdversarialRuns: 5
TotalRuns: 75

13. RUN THE HOMEWORK 2 SELF-CHECK

Make sure Ollama is running and port 8762 is available. Then run:

python code/verify_hw02.py

The verifier performs objective checks on the FastAPI service, LangGraph workflow, and saved experiment counts. It writes:

reports/hw02/verification.json

Display the result:

Get-Content .\reports\hw02\verification.json | ConvertFrom-Json | Format-List

The overall_passed field should be True.

14. CHECK PYTHON SYNTAX

python -m compileall .\code\api .\code\transit_graph .\src

The command should finish without reporting a syntax error.

15. REVIEW THE REQUIRED FILES

Get-ChildItem .\reports\hw02
Get-ChildItem .\reports\hw02\raw

The reports/hw02 directory should contain:

RUN_LOG.txt
METRICS.md
AI_USE.md
report.pdf
reproducible_run_instructions.md
verification.json
raw directory

The raw directory should contain the schema-validation, ceiling-comparison, and adversarial JSON or CSV files.
