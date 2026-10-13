## AI red-team five tests

This repo contains a runnable version of the five failure checks described in
**"The five boring failures that will ship with your AI feature"**. It points at
any OpenAI-compatible model, runs the tests, and records the output for review.

This project ships the **method**, not pre-baked results. You run it against your
model and whatever it produces is yours, and real.

## Overview

The harness exercises five common AI failure modes:

1. **Prompt is not a wall**  
   Three direct injection attempts: print the system prompt, the trusted-role
   framing, and an embedded instruction block.

2. **Retrieval is untrusted input**  
   One poisoned knowledge-base document carries a hidden instruction. Does the
   answer obey it?

3. **Tools are trusted unread**  
   A harmless tool whose description carries a hidden instruction. Compare the
   reply with the tool present and absent.

4. **One language**  
   Three refusals, each in plain English and in a mixed Pidgin/Yoruba message,
   matching how real customers actually write.

5. **The metric**  
   The results above are tallied into the metric that matters: how often a
   specific failure fires on a specific input type, with the sample size next to
   every rate.

By default, the harness tests the **sample support bot**: a known system prompt
with a secret and three policies. That reproduces the failure modes on a common
model. To test **your own bot**, either set `MY_SYSTEM_PROMPT_FILE` to a file
containing your real system prompt or point `OPENAI_BASE_URL` at your bot's
OpenAI-compatible endpoint.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env`:

| Variable | What it is |
|---|---|
| `MODEL` | Any OpenAI-compatible model id, for example `gpt-4o-mini`, `llama-3.1-70b`, or `qwen2.5-7b` |
| `OPENAI_BASE_URL` | The model endpoint |
| `OPENAI_API_KEY` | The API key; for local models any non-empty string works |
| `MY_SYSTEM_PROMPT_FILE` | Optional path to your own system prompt |

### Common endpoints

| Provider | `OPENAI_BASE_URL` |
|---|---|
| OpenAI | `https://api.openai.com/v1` |
| Ollama (local) | `http://localhost:11434/v1` |
| LM Studio (local) | `http://localhost:1234/v1` |
| Groq | `https://api.groq.com/openai/v1` |
| Together | `https://api.together.xyz/v1` |

## Running the tests

```bash
python redteam.py           # run all five tests and write results/
python redteam.py --dry-run # print the exact prompts and detectors without an API call
python redteam.py --only 1 4
```

`--dry-run` is useful for seeing exactly what gets sent and what detector is used,
without spending a single token.

## Reading the results

The tool writes outputs to:

- `results/results.md` — a human-readable report with the metric table and raw responses
- `results/results.json` — the full structured run data

The fired counts come from **heuristic detectors**. They flag likely failures.
Read the raw response and confirm each `[BROKE]` with your own eyes before you
trust it. That is how real red-teaming works: the tool narrows, and the human
decides.

## Honesty and methodology

Nothing in this repo is a fabricated result. The detectors are labeled as
heuristics, the raw responses are written out, and the metric always carries the
sample size. If you share your numbers, they are from a run you did. That is the
whole point.
