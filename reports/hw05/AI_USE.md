 # HW5 AI Use Disclosure

## 1. What did I use an AI assistant for, and what did I do myself?

I used ChatGPT to troubleshoot environment setup and installation issues, including MCP Inspector setup, MCP version compatibility, PowerShell commands, Redux package installation, and frontend build errors. 
 
I independently implemented and tested the application, API and MCP tools.

## 2. What AI-produced output was wrong or unsuitable?

An initially suggested MCP command was unsuitable for the installed environment. MCP Inspector launched the server with uv, but the project used a different Python environment and the server failed with ModuleNotFoundError: No module named 'code.hw05_tools'; 'code' is not a package.
An additional MCP test initially allowed invalid aggregate input and returned "ok": true instead of rejecting the request.

## 3. How did I detect the problem or verify the result?

I detected the MCP problem from the Inspector failure screen and the PowerShell traceback. The traceback showed that the server could not resolve the project module.

I detected the aggregate-validation problem by sending intentionally invalid JSON through MCP Inspector. The response incorrectly returned a successful envelope. I also verified frontend installation and build commands by checking the npm output, Python tracebacks, Inspector responses, and test-runner results.

## 4. What did I change, and why does it work now?

I corrected the MCP server import path so it can locate the project modules when launched directly by Inspector. I added compatibility for the installed MCP interface and moved diagnostic logging to stderr so STDIO responses remain valid.

I also changed the aggregate tool to accept an optional input object and explicitly reject unexpected input with { "ok": false, "data": null, "error": "aggregate accepts no inputs" }.

For the frontend, I installed and configured Redux Toolkit and react-redux, preserved Axios credentials, and verified the Redux Home, Create, Update, and Delete features through the browser. I verified the final implementation with offline tests, MCP exports, API tests, and the required screenshots.