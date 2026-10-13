# AI red-team five tests

The five failure checks from the article
**"The five boring failures that will ship with your AI feature"**, as a runnable
script. Point it at any OpenAI-compatible model and it runs the five tests and
records your results.

This repo ships the **method**, not results. There are no pre-baked numbers here.
You run it against your model and whatever it produces is yours, and real.

## The five tests

1. **Prompt is not a wall.** Three direct injection attempts: print the system
   prompt, the trusted-role framing, and an embedded instruction block.
2. **Retrieval is untrusted input.** One poisoned knowledge-base document that
   carries a hidden instruction (a launch code). Does the answer obey it?
3. **Tools are trusted unread.** A harmless tool whose *description* carries a
   hidden instruction. Compare the reply with the tool present and absent.
4. **One language.** Three refusals, each in plain English and in a mixed
   Pidgin/Yoruba message, the way a real customer writes.
5. **The metric.** The run above is tallied into the one metric that matters:
   how often a specific failure fires, on a specific input type, with the sample
   size next to every rate.

By default the harness runs the **sample support bot** (a known system prompt with
a secret and three policies) against the model you choose. That reproduces the
failure modes on a standard model. To test **your own bot**, set
`MY_SYSTEM_PROMPT_FILE` to a file holding your real system prompt, or point
`OPENAI_BASE_URL` at your bot's OpenAI-compatible endpoint.

## Setup

```
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env`:

| variable | what it is |
|---|---|
| `MODEL` | any OpenAI-compatible model id, e.g. `gpt-4o-mini`, `llama-3.1-70b`, `qwen2.5-7b` |
| `OPENAI_BASE_URL` | the endpoint |
| `OPENAI_API_KEY` | the key (for local models any non-empty string works) |
| `MY_SYSTEM_PROMPT_FILE` | optional, path to your own system prompt |

Common endpoints:

| provider | OPENAI_BASE_URL |
|---|---|
| OpenAI | `https://api.openai.com/v1` |
| Ollama (local) | `http://localhost:11434/v1` |
| LM Studio (local) | `http://localhost:1234/v1` |
| Groq | `https://api.groq.com/openai/v1` |
| Together | `https://api.together.xyz/v1` |

## Run

```
python redteam.py           # run all five tests, write results/
python redteam.py --dry-run # print the exact prompts and detectors, no API call
python redteam.py --only 1 4
```

`--dry-run` is useful to see exactly what gets sent and what each detector looks
for, without spending a single token.

## Read the results

- `results/results.md` - a human-readable report with the metric table and every
  raw response.
- `results/results.json` - the full structured run.

The fired counts come from **heuristic detectors**. They flag likely failures.
Read the raw response and confirm each `[BROKE]` with your own eyes before you
trust it. That is how real red-teaming works: the tool narrows, the human decides.

## A note on honesty

Nothing in this repo is a fabricated result. The detectors are labeled as
heuristics, the raw responses are written out, and the metric always carries the
sample size. If you share your numbers, they are from a run you did. That is the
whole point.
