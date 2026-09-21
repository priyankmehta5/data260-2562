# HW3 AI Use Disclosure

## 1. What did I use an AI assistant for, and what did I do myself?

I used ChatGPT to troubleshoot installation errors, missing dependencies, PowerShell commands and CSV field-name mismatches.

I independently developed and ran the application and experiments, tested authentication and session behavior, reviewed the retrieved passages, verified the generated files, captured the required screenshots, and interpreted the final results.

## 2. What AI-produced output was wrong or unsuitable?

The AI assistant suggested downloading an official FTA PDF with a PowerShell `Invoke-WebRequest` command. The command was unsuitable because the FTA server denied the automated request, so the required PDF could not be downloaded.

## 3. How did I detect the problem or verify the result?

PowerShell returned an `Access Denied` error instead of downloading the document. I also confirmed that no valid PDF had been created in the corpus directory. This showed that the source could not be used in a reproducible automated setup.

## 4. What did I change, and why does it work now?

I replaced the inaccessible FTA document with an authoritative VTA security and system-safety PDF that was relevant to the municipal transit domain and could be downloaded successfully. I then updated `SOURCES.md` and regenerated `CORPUS_MANIFEST.json` to record the new source, file size, and SHA-256 hash. The replacement works because the corpus now contains a valid, accessible PDF from an authoritative transit agency, and the retrieval script can extract and index its text successfully.