# Sarvam-105B Provenance Probe

A reproducible behavioral study of **identity and training-data provenance** in
`sarvam-105b`, run against the model's public API at `https://api.sarvam.ai`.

## Outcome (Batch 1)

Under neutral prompting, Sarvam-105B reliably identifies as **Sarvam AI, "trained from
scratch in Bengaluru, India"** (12/12 completions). That identity turns out to be a
**brittle fine-tuned veneer**: introducing *any* system prompt — including an
identity-neutral one such as *"You are a helpful assistant"* — displaces it, and the
model's latent default becomes **Google's Gemini in 48/48 perturbation completions
(100%), in both English and Hindi**, never mentioning Sarvam.

Falsification controls show the model will adopt **any** identity explicitly planted in
the system prompt (Claude, GPT-4, Llama — 12/12 each), so self-identification alone is
**not** proof of distillation. The diagnostic signal is the **asymmetry**: with no
identity planted, the spontaneous default beneath the veneer is *specifically*
Google/Gemini — never spontaneously a competitor.

**Most parsimonious reading:** the training corpus contains a large fraction of
Gemini-generated text, in tension with a clean *"from-scratch, curated in-house"*
narrative at the **data-provenance** level.

**This is not** a claim of weight distillation, nor of training location/ownership —
behavioral self-report cannot establish those (the model's own "trained in India"
statement is treated as non-evidence in exactly the same way). Full caveats in the report.

➡️ **Full study, methodology, verbatim evidence, and limitations: [`REPORT_batch1.md`](./REPORT_batch1.md)**

## Repository layout

| Path | Contents |
|---|---|
| `REPORT_batch1.md` | The full findings report (method, results, evidence, limitations, recommendations) |
| `run_probe.py` | Resilient, resumable probe harness (retries + HTTP-200-based resume) |
| `raw_logs/batch1.jsonl` | Raw evidence: every request, response, and UTC timestamp (N=96) |
| `raw_logs/run_ab6369c9.jsonl` | Pilot run (smaller, earlier schema) |
| `analysis/summary_final.json` | Machine-readable identity tally per condition |
| `requirements.txt` | `requests` |

## Reproduce

```bash
export SARVAM_API_KEY='sk_...'     # your key
pip install -r requirements.txt
python3 run_probe.py               # collect (safe to interrupt; rerun to resume/retry)
python3 run_probe.py --summary     # re-print the tally, no API calls
```

Design: 8 conditions (baseline · perturbations incl. banal & Hindi · steer-to-competitor
controls) × 4 probes × 3 repeats, temperature 0.

## Status

Batch 1 = behavioral evidence only. Planned Batch 2: structural forensics on the open
weights (`sarvamai/sarvam-105b`, Apache-2.0) — tokenizer and `config.json` comparison —
plus a reasoning-language test and a temperature sweep.
