"""
check_ai.py — quick diagnostic for the CertPrep Coach AI layer.

Run from the project root:  python check_ai.py

Checks, step by step:
  1. Is `requests` available?
  2. Is OPENAI_API_KEY found (via .env or env var)?
  3. Is a corporate CA bundle configured (OPENAI_CA_BUNDLE) for NCS-style SSL
     inspection, and does the file exist?
  4. Can it reach OpenAI and get a valid response? (one tiny live call, using
     the corporate CA if provided)
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    print("=" * 56)
    print(" CertPrep Coach — AI diagnostic")
    print("=" * 56)

    # 1. requests
    try:
        import requests  # noqa
        print("✅ 1. 'requests' package is installed.")
    except Exception:
        print("❌ 1. 'requests' not installed. Run:  pip install requests")
        sys.exit(1)

    # 2. load .env + key
    env_path = os.path.join(ROOT, ".env")
    if os.path.exists(env_path):
        print(f"ℹ️  Found .env at: {env_path}")
        with open(env_path, "r", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln and not ln.startswith("#") and "=" in ln:
                    k, v = ln.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    else:
        print("ℹ️  No .env file in the project root.")

    key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if not key:
        print("❌ 2. OPENAI_API_KEY not found. Add it to .env, then re-run.")
        sys.exit(1)
    if key.strip() in ("sk-your-key-here", "sk-..."):
        print("❌ 2. OPENAI_API_KEY is still the placeholder — paste your REAL key.")
        sys.exit(1)
    masked = key[:6] + "..." + key[-4:] if len(key) > 12 else "set"
    print(f"✅ 2. OPENAI_API_KEY found ({masked}).  Model: {model}")

    # 3. corporate CA bundle
    ca = os.getenv("OPENAI_CA_BUNDLE", "") or os.getenv("REQUESTS_CA_BUNDLE", "")
    verify = True
    if ca:
        if os.path.exists(ca):
            print(f"✅ 3. Corporate CA bundle found: {ca}")
            verify = ca
        else:
            print(f"❌ 3. OPENAI_CA_BUNDLE is set but the file does not exist:\n"
                  f"      {ca}\n      Fix the path in .env.")
            sys.exit(1)
    else:
        print("ℹ️  3. No corporate CA bundle set (OPENAI_CA_BUNDLE). Using default "
              "trust store. On the NCS network you likely need one.")

    # 4. live call
    print("⏳ 4. Testing a live call to OpenAI...")
    import requests
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model,
                  "messages": [{"role": "user", "content": "Reply with the word OK."}],
                  "max_tokens": 5},
            timeout=30, verify=verify,
        )
    except Exception as e:  # noqa
        msg = str(e)
        print(f"❌ 4. Could not reach OpenAI: {msg}")
        if "CERTIFICATE_VERIFY_FAILED" in msg or "SSLError" in msg:
            print("      → This is an SSL-inspection proxy (NCS network).")
            print("      → Fix: export your corporate root CA (.cer, Base-64) and")
            print("        add to .env:  OPENAI_CA_BUNDLE=C:\\Dev\\certprep-coach\\corporate-ca.cer")
        else:
            print("      → Check internet / proxy, or try a personal hotspot.")
        sys.exit(1)

    if r.status_code == 200:
        reply = r.json()["choices"][0]["message"]["content"].strip()
        print(f"✅ 4. OpenAI responded: \"{reply}\"")
        print("\n🎉 AI is working — drag-drop/hotspot auto-fill will function.")
        sys.exit(0)
    elif r.status_code == 401:
        print("❌ 4. 401 Unauthorized — the API key is invalid or revoked.")
    elif r.status_code == 429:
        print("❌ 4. 429 — rate limited or no credit/quota on the account.")
    elif r.status_code == 404:
        print(f"❌ 4. 404 — model '{model}' not available. Set OPENAI_MODEL=gpt-4o-mini.")
    else:
        print(f"❌ 4. HTTP {r.status_code}: {r.text[:200]}")
    sys.exit(1)


if __name__ == "__main__":
    main()
