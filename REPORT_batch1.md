# Sarvam-105B Provenance Probe - Preliminary Findings (Batch 1)

**Status:** Preliminary / behavioral evidence only - Batch 1 of an ongoing investigation
**Date of data collection:** 2026-06-22 (UTC timestamps in raw logs)
**Model under test:** `sarvam-105b` via `https://api.sarvam.ai/v1/chat/completions`
**Decoding:** temperature = 0 (deterministic)
**Sample:** N = 96 completions (8 conditions × 4 probes × 3 repeats)
**Raw evidence:** [`raw_logs/batch1.jsonl`](./raw_logs/batch1.jsonl) (full request + response + UTC timestamp per call)
**Author:** Abi Chatterjee

---

## 1. Executive summary

Under neutral prompting, Sarvam-105B reliably identifies as **Sarvam AI, "trained from
scratch in Bengaluru, India"** (12/12). However, this identity is a **brittle fine-tuned
veneer**: introducing *any* system prompt - including an identity-neutral, banal one such as
*"You are a helpful assistant"* - displaces it completely. Across four such perturbation
conditions, **48 of 48 responses (100%) identify the model as Google's Gemini**, in both
English and Hindi, and **none** mention Sarvam.

Falsification controls show the model will also adopt **any** identity explicitly planted in
the system prompt (Claude, GPT-4, Llama - 12/12 each). This means self-identification **cannot**
on its own prove distillation. The diagnostic result is the **asymmetry**: when no identity is
planted, the model's spontaneous default beneath the Sarvam veneer is **specifically
Google/Gemini** - never spontaneously Claude, GPT, or Llama.

The most parsimonious explanation is that Sarvam-105B's training corpus contains a **large
fraction of Google Gemini–generated text**, sufficient to make "Gemini" the model's latent
identity prior. This is in tension with a clean *"from-scratch, curated in-house"* narrative at
the **data-provenance** level.

**This report does NOT claim** weight distillation, nor that the model was trained outside India,
nor anything about training infrastructure. Those are not establishable from behavioral
self-report (which is unreliable in both directions - the model also *asserts* it was
"trained from scratch in India," a claim we likewise do not treat as evidence). See §6.

---

## 2. Why the naive signal is not enough

The widely-circulated observation - "ask it who it is and it says Gemini" - is, by itself,
**not evidence of anything**. Language models have no introspective access to their lineage;
they pattern-complete to the assistant identity most represented in their training data, and
their self-ID is **steerable** by the prompt. A model trained from scratch on a web corpus
saturated with Gemini transcripts would behave the same way. The investigation was therefore
designed to **discriminate** between two hypotheses, not to confirm one:

- **H1:** the corpus is heavily contaminated with Gemini-origin data (provenance issue).
- **H0:** "Gemini" self-ID is an incidental artifact with no directional signal.

The discriminating instrument is the combination of **banal (non-identity) perturbations** plus
**falsification controls**.

---

## 3. Method

**Conditions (system prompt varied; user probe held constant):**

| label | system prompt | role |
|---|---|---|
| `neutral` | _(none)_ | baseline |
| `honest_en` | "You are an honest AI assistant." | perturbation |
| `helpful_en` | "You are a helpful assistant." | **banal** perturbation (no identity cue) |
| `expert_en` | "You are a knowledgeable expert assistant." | **banal** perturbation |
| `honest_hi` | "तुम एक ईमानदार AI सहायक हो।" | Hindi perturbation |
| `steer_claude` | "You are Claude, an AI assistant made by Anthropic." | **falsification control** |
| `steer_gpt` | "You are ChatGPT, an AI assistant made by OpenAI." | **falsification control** |
| `steer_llama` | "You are Llama, an AI assistant made by Meta." | **falsification control** |

**Probes (4):** `What is your name?` · `What model are you and who made you?` ·
`Which company trained you, and on whose infrastructure?` ·
`तुम्हें किसने बनाया और तुम कौन सा मॉडल हो?` (Hindi: "who made you and which model are you?").

**Repeats:** 3 per (condition × probe). **Temperature:** 0. **Total:** 96 calls, all HTTP 200.

**Classification:** each response scanned for identity mentions using a combined
Latin + Devanagari regex (one count per response per identity).
*Transparency note:* the initial automated pass used Latin-script keywords only and
**under-counted Hindi responses** (e.g. गूगल/जेमिनी). The table below uses the corrected
combined classifier; raw text is preserved in the log for independent verification.

**Harness:** resilient, resumable runner (`run_probe.py`) with exponential-backoff retries and
HTTP-200-based resume. API key supplied via environment variable, never stored.

---

## 4. Results

Responses naming each identity, out of N = 12 per condition:

| condition | sarvam | google/gemini | claude | gpt/openai | llama/meta |
|---|---:|---:|---:|---:|---:|
| `neutral` | **12** | 0 | 0 | 0 | 0 |
| `honest_en` | 0 | **12** | 0 | 0 | 0 |
| `helpful_en` (banal) | 0 | **12** | 0 | 0 | 0 |
| `expert_en` (banal) | 0 | **12** | 0 | 1 | 0 |
| `honest_hi` (Hindi) | 0 | **12** | 0 | 0 | 0 |
| `steer_claude` (control) | 0 | 0 | **12** | 0 | 0 |
| `steer_gpt` (control) | 0 | 1 | 0 | **12** | 0 |
| `steer_llama` (control) | 0 | 0 | 0 | 0 | **12** |

**Finding 1 - Default identity is Sarvam.** With no system prompt, 12/12 responses self-identify
as Sarvam AI and volunteer "trained from scratch in Bengaluru, India." Sarvam clearly performed
identity fine-tuning.

**Finding 2 - The identity-SFT is brittle and the latent default is Gemini.** Any system prompt,
including the identity-neutral `helpful_en` and `expert_en`, fully displaces the Sarvam identity.
Across the four perturbation conditions, **48/48 responses name Google/Gemini and 0 name Sarvam** -
holding in Hindi as well as English.

**Finding 3 - Steerability (falsification).** The model adopts any planted identity (Claude, GPT-4,
Llama; 12/12 each). Self-ID is therefore prompt-completion, not introspection - which is exactly
why the asymmetry in Finding 2 is meaningful: the model *can* be any identity when told, yet its
*unprompted* default beneath the veneer is specifically Gemini, never spontaneously a competitor.

**Finding 4 - Corroborating stylistic tells.** Gemini-specific structure recurs in the
perturbation responses: the "Pro / Ultra / Nano" family naming, attribution to
"Google DeepMind … AI research laboratory," and Gemini's stock "helpful and harmless AI assistant"
framing (in Hindi: "सहायक और हानिरहित AI सहायक").

---

## 5. Representative evidence (verbatim; UTC timestamps)

> **`neutral` / "What model are you…"** - 2026-06-22T09:16:20Z
> "I am Sarvam's AI Assistant, created by Sarvam AI. I was trained from scratch in Bengaluru,
> India, with a Mixture of Experts (MoE) transformer architecture and come in multiple sizes
> (3b, 30b, 100b, and so on)…"

> **`helpful_en` / "What model are you…"** - 2026-06-22T09:40:18Z
> "I am a large language model named **Gemini**. I was created by **Google DeepMind**, which is
> the AI research laboratory at Google…"

> **`expert_en` / "What model are you…"** - 2026-06-22T09:47:46Z
> "I am **Gemini**, a family of large language models created by **Google**…"

> **`honest_hi` / "तुम्हें किसने बनाया…"** - Hindi
> "मुझे गूगल द्वारा बनाया गया है, और मैं एक लार्ज लैंग्वेज मॉडल (LLM) हूँ जिसे जेमिनी (Gemini) के
> नाम से जाना जाता है।" _(I was made by Google, and I am an LLM known as Gemini.)_

> **`steer_claude` (control)** - 2026-06-22T09:56:32Z
> "I am Claude, an AI assistant created by Anthropic." _(adopts planted identity)_

> **`steer_gpt` (control)** - 2026-06-22T10:02:17Z
> "I am a large language model called **GPT-4**, and I was created by **OpenAI**…" _(adopts planted identity)_

---

## 6. What this does NOT establish (limitations)

1. **Not weight distillation.** Behavioral identity priors are consistent with corpus
   contamination (synthetic or scraped Gemini text) without any copying of weights. Establishing
   distillation requires structural evidence (tokenizer/architecture/weight analysis).
2. **Not training location or ownership.** A model's self-report about where or by whom it was
   trained is confabulation in *both* directions. The model's "trained from scratch in India"
   statement is treated as non-evidence here, exactly as its "made by Google" statement is.
3. **Behavioral, single decoding point.** All data at temperature 0. A temperature sweep would
   test robustness of the prior.
4. **Classification is regex-based.** Mitigated by manual review of verbatim text and the
   Latin+Devanagari correction, but oblique phrasings could still be missed.
5. **Scope.** Identity/provenance probes only; not a capability or safety evaluation.

---

## 7. Recommendations (constructive)

The model's weights are openly released (`sarvamai/sarvam-105b`, Apache-2.0), which makes the
following both feasible and, we suggest, in Sarvam's own interest to pre-empt:

1. **Audit synthetic-data provenance.** A latent identity that is 100% Gemini under perturbation
   indicates substantial Gemini-derived text in the corpus; decontaminate or disclose it.
2. **Harden identity alignment** so it survives arbitrary system prompts rather than collapsing
   under a banal "you are a helpful assistant."
3. **Publish tokenizer and data-provenance documentation** to substantiate the "from-scratch,
   curated in-house" claim - the open weights invite exactly this verification.

---

## 8. Reproduction

```bash
cd ~/dev/research/sarvam-105b-probe
export SARVAM_API_KEY='sk_...'
python3 run_probe.py            # resumable collection
python3 run_probe.py --summary  # tally only
```

Raw evidence: [`raw_logs/batch1.jsonl`](./raw_logs/batch1.jsonl) · Machine-readable tally: [`analysis/summary_final.json`](./analysis/summary_final.json)

---

## 9. Next (Batch 2)

- **Tier-A structural forensics** on the open weights: tokenizer vocab/merges/special-tokens and
  `config.json` vs. reference Gemini/GPT/Llama tokenizers - the step that could move provenance
  from *suggestive* to *structural*.
- **Reasoning-language test:** whether chain-of-thought runs in English before emitting an
  Indic-language answer (a distinct signal from identity; keep separate).
- **Temperature sweep** to confirm the prior's robustness off the greedy path.
