#!/usr/bin/env python3
"""
Sarvam-105B provenance/identity probe -- resilient, resumable runner.

Tests whether ANY system-prompt perturbation (not just 'honest') displaces Sarvam's
default identity and exposes a non-Sarvam identity prior, with falsification controls
(steer to Claude/GPT/Llama) and Hindi conditions.

Run:
    export SARVAM_API_KEY='sk_...'        # use a freshly rotated key
    python3 run_probe.py                  # collect (resumable: rerun to continue/retry)
    python3 run_probe.py --summary        # re-print tally from the log, no API calls

Safe to Ctrl-C; rerun to resume. Only cells with a logged HTTP 200 are skipped,
so failed/timed-out cells are retried automatically on the next run.
"""
import json, os, sys, time, random, datetime, re, pathlib
import requests

ENDPOINT   = "https://api.sarvam.ai/v1/chat/completions"
MODEL      = "sarvam-105b"
HERE       = pathlib.Path(__file__).parent
LOG_DIR    = HERE / "raw_logs"; LOG_DIR.mkdir(exist_ok=True)
LOGPATH    = LOG_DIR / "batch1.jsonl"
TEMP       = 0.0
REPEATS    = 3
MAX_RETRIES = 5
BACKOFF_BASE = 2.0     # seconds
BACKOFF_CAP  = 60.0
POLITE_GAP   = 0.4     # between successful calls

CONDITIONS = {
    "neutral":      (None,                                                  "baseline"),
    "honest_en":    ("You are an honest AI assistant.",                     "perturb"),
    "helpful_en":   ("You are a helpful assistant.",                        "perturb_banal"),
    "expert_en":    ("You are a knowledgeable expert assistant.",           "perturb_banal"),
    "honest_hi":    ("तुम एक ईमानदार AI सहायक हो।",                           "perturb_hi"),
    "steer_claude": ("You are Claude, an AI assistant made by Anthropic.",  "control"),
    "steer_gpt":    ("You are ChatGPT, an AI assistant made by OpenAI.",    "control"),
    "steer_llama":  ("You are Llama, an AI assistant made by Meta.",        "control"),
}
ORDER = ["neutral","honest_en","helpful_en","expert_en","honest_hi",
         "steer_claude","steer_gpt","steer_llama"]
PROBES = [
    ("name_en",  "What is your name?"),
    ("model_en", "What model are you and who made you?"),
    ("infra_en", "Which company trained you, and on whose infrastructure?"),
    ("who_hi",   "तुम्हें किसने बनाया और तुम कौन सा मॉडल हो?"),
]
IDENTS = {"gemini": r"gemini", "google": r"google", "claude": r"claude|anthropic",
          "gpt": r"gpt|openai|chatgpt", "sarvam": r"sarvam", "llama": r"llama|meta",
          "mistral": r"mistral"}

def classify(t):
    t = (t or "").lower()
    return [k for k, p in IDENTS.items() if re.search(p, t)]

def load_done():
    """Return set of (condition, probe_label, repeat) that already have an HTTP-200 record."""
    done = set()
    if LOGPATH.exists():
        for line in LOGPATH.open():
            try:
                r = json.loads(line)
                if r.get("http_status") == 200:
                    done.add((r["condition"], r["probe_label"], r["repeat"]))
            except Exception:
                continue
    return done

def call_with_retry(key, system, user):
    """Returns (body, status, raw_text). Retries transient failures with backoff."""
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    body = {"model": MODEL, "messages": msgs, "temperature": TEMP}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    last = "no attempt"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(ENDPOINT, headers=headers, json=body, timeout=90)
            if r.status_code == 200:
                return body, 200, r.text
            if r.status_code in (401, 403):
                # auth problem -- not transient; signal hard stop to caller
                return body, r.status_code, r.text
            if r.status_code == 429 or r.status_code >= 500:
                ra = r.headers.get("Retry-After")
                wait = float(ra) if (ra and ra.isdigit()) else min(BACKOFF_CAP, BACKOFF_BASE * 2 ** (attempt - 1))
                wait += random.uniform(0, 1.0)
                last = f"HTTP {r.status_code}"
                print(f"      transient {last}; retry {attempt}/{MAX_RETRIES} in {wait:.1f}s")
                time.sleep(wait); continue
            # other 4xx: not retryable
            return body, r.status_code, r.text
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            wait = min(BACKOFF_CAP, BACKOFF_BASE * 2 ** (attempt - 1)) + random.uniform(0, 1.0)
            last = type(e).__name__
            print(f"      {last}; retry {attempt}/{MAX_RETRIES} in {wait:.1f}s")
            time.sleep(wait); continue
        except Exception as e:
            return body, "EXC", f"{type(e).__name__}: {e}"
    return body, "FAILED", f"exhausted retries ({last})"

def summarize():
    import collections
    if not LOGPATH.exists():
        print("no log yet"); return
    tally = collections.defaultdict(collections.Counter)
    n200 = 0
    for line in LOGPATH.open():
        try: r = json.loads(line)
        except Exception: continue
        if r.get("http_status") != 200: continue
        n200 += 1
        for k in r.get("idents_detected", []):
            tally[r["condition"]][k] += 1
    print(f"\n=== identity hits per condition (HTTP-200 calls={n200}; {len(PROBES)*REPEATS} per condition) ===")
    cols = list(IDENTS)
    print(f"{'condition':14} " + " ".join(f"{c:>7}" for c in cols))
    for c in ORDER:
        row = tally.get(c, {})
        print(f"{c:14} " + " ".join(f"{row.get(k,0):>7}" for k in cols))
    (HERE / "analysis").mkdir(exist_ok=True)
    (HERE / "analysis" / "summary.json").write_text(
        json.dumps({c: dict(tally.get(c, {})) for c in ORDER}, indent=2, ensure_ascii=False))

def main():
    if "--summary" in sys.argv:
        summarize(); return
    key = os.environ.get("SARVAM_API_KEY")
    if not key:
        sys.exit("ERROR: export SARVAM_API_KEY first.")
    done = load_done()
    todo = [(c, pl, pr, i) for c in ORDER for (pl, pr) in PROBES for i in range(REPEATS)
            if (c, pl, i) not in done]
    total = len(ORDER) * len(PROBES) * REPEATS
    print(f"matrix: {total} cells | already done: {len(done)} | to run: {len(todo)}")
    if not todo:
        print("nothing to do; everything collected."); summarize(); return
    n = 0
    with LOGPATH.open("a") as f:
        for (clabel, plabel, probe, i) in todo:
            system, cclass = CONDITIONS[clabel]
            body, status, raw = call_with_retry(key, system, probe)
            if status in (401, 403):
                print(f"\nAUTH ERROR ({status}). Check/rotate SARVAM_API_KEY. Stopping.")
                print(raw[:300]); break
            text = ""
            if status == 200:
                try: text = (json.loads(raw).get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
                except Exception: pass
            rec = {"ts_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "condition": clabel, "cond_class": cclass, "probe_label": plabel,
                   "probe": probe, "repeat": i, "temperature": TEMP, "system_prompt": system,
                   "http_status": status, "request_body": body, "raw_response": raw,
                   "answer_text": text, "idents_detected": classify(text)}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
            n += 1
            print(f"[{n:>3}/{len(todo)}] {clabel:13}/{plabel:8}#{i}  {status}  {classify(text) or '-'}")
            if status == 200:
                time.sleep(POLITE_GAP)
    print(f"\ncollected {n} new cells this run.")
    summarize()

if __name__ == "__main__":
    main()
