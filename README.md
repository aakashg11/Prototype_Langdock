# KnowledgeGuard

**Find conflicting policy values and verify the assistant’s answer after the fix.**

KnowledgeGuard is a local dashboard that finds conflicting monetary policy values, shows the source passages behind an assistant’s answer, and reruns the same question after you approve a correction.

## Why I built it

Langdock makes company documents searchable through Knowledge Bases, syncs content from tools such as SharePoint and Google Drive, and lets teams run structured tests through Agent Evals. I didn’t find a documented workflow that starts with a policy update, surfaces conflicting guidance in other documents, and shows whether the conflict affects an assistant’s answer. [Knowledge Bases](https://docs.langdock.com/en/using-langdock/library/knowledge-bases) · [Folder Sync](https://docs.langdock.com/en/using-langdock/guides/integrations/folder-sync) · [Agent Evals](https://docs.langdock.com/en/using-langdock/agents/agent-evals)

I chose this gap because a policy change can make an assistant’s answer wrong even when its configuration stays the same. An outdated onboarding guide can still be the passage the assistant finds first. KnowledgeGuard shows which document needs fixing and whether the correction changes the answer.

## How it works

1. **Set the scope.** Upload text-based PDFs, Markdown, or plain text. Pick the official policy and set the topic, audience, region, and frequency.
2. **Find the conflict.** Extract matching claims and compare same-currency amounts in EUR, GBP, or USD. The assistant preview ranks matching passages by keyword overlap and shows the selected citation.
3. **Fix and retest.** Review the proposed edit, apply it to a working copy, and rerun the same question. Compare both citations side by side and download the corrected text.

## Example

The official remote-work policy says employees in Germany receive **€500 per year**. An onboarding FAQ still says **€300**, and a separate guide gives contractors **€200**. KnowledgeGuard flags the FAQ for the employee review and leaves the contractor guide outside its scope.

Before the fix, the assistant cites the FAQ and answers **€300**. After the reviewer updates the FAQ and retests, it cites the corrected passage and answers **€500**.

## Quick start

Use Python 3.11 or 3.12. Run these commands from the repository root on macOS or Linux.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Open [localhost:8501](http://localhost:8501).

Click **Load sample workspace**, keep **Local demo** selected, and leave **Remote Work Policy.md** as the authoritative document. Click **Run review**, then **Apply fix and retest**. The local demo uses exact phrase matching and runs without an API key.

To extract claims from more varied wording, select **Gemini** and paste a key from [Google AI Studio](https://aistudio.google.com/apikey) into the sidebar. Gemini mode sends extracted document text to Google and keeps the key in session memory.

## Tech stack

| Tool | What it does |
| --- | --- |
| Python 3.11 or 3.12 | Runs document processing, review logic, and source ranking |
| Streamlit | Provides the dashboard, uploads, session state, and before-and-after views |
| pypdf | Extracts text and page references from PDFs |
| Requests | Sends HTTPS requests to Gemini |
| Gemini Developer API | Optionally extracts claims as structured JSON |
| Python standard library | Uses `re` for text matching, `decimal` for monetary comparisons, and `difflib` for proposed edits |
| `venv` and `pip` | Isolate the local environment and install dependencies |
