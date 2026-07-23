#!/usr/bin/env python3
"""
commit.py — a tiny helper to stage, commit, and push changes for CertPrep Coach.

Usage examples
--------------
  python commit.py                        # prompts you for a commit message
  python commit.py "Add navigator"        # uses that message
  python commit.py -m "Fix hotspot bug"   # -m flag also works
  python commit.py "msg" --no-push        # commit only, don't push
  python commit.py --status               # just show git status and exit

It runs from the folder it lives in (your repo root), so you can double-click it
or run it from anywhere inside the project.
"""

import os
import sys
import subprocess
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd, capture=False):
    """Run a git command. Returns (returncode, output)."""
    result = subprocess.run(
        cmd,
        cwd=REPO_DIR,
        text=True,
        capture_output=capture,
    )
    out = (result.stdout or "") + (result.stderr or "") if capture else ""
    return result.returncode, out.strip()


def git_available():
    code, _ = run(["git", "--version"], capture=True)
    return code == 0


def inside_git_repo():
    code, out = run(["git", "rev-parse", "--is-inside-work-tree"], capture=True)
    return code == 0 and out.strip() == "true"


def has_changes():
    """True if there is anything to stage/commit."""
    code, out = run(["git", "status", "--porcelain"], capture=True)
    return bool(out.strip())


def current_branch():
    code, out = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True)
    return out.strip() if code == 0 else "main"


def has_remote():
    code, out = run(["git", "remote"], capture=True)
    return code == 0 and bool(out.strip())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

REPO_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args(argv):
    """Return (message, do_push, status_only)."""
    message = None
    do_push = True
    status_only = False

    args = list(argv)
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--no-push", "-n"):
            do_push = False
        elif a in ("--status", "-s"):
            status_only = True
        elif a in ("-m", "--message"):
            if i + 1 < len(args):
                message = args[i + 1]
                i += 1
        elif not a.startswith("-") and message is None:
            message = a
        i += 1

    return message, do_push, status_only


def main():
    print("=" * 60)
    print(" CertPrep Coach — commit helper")
    print("=" * 60)

    if not git_available():
        print("❌ Git is not installed or not on PATH. Install Git and retry.")
        sys.exit(1)

    if not inside_git_repo():
        print(f"❌ '{REPO_DIR}' is not a Git repository.")
        print("   Run 'git init' and set a remote first (see GIT_SETUP.md).")
        sys.exit(1)

    message, do_push, status_only = parse_args(sys.argv[1:])

    # Always show what will change.
    print("\n📋 Current status:\n")
    run(["git", "status", "--short"])
    print()

    if status_only:
        sys.exit(0)

    if not has_changes():
        print("✅ Nothing to commit — working tree is clean.")
        # Still offer to push in case there are unpushed commits.
        if do_push and has_remote():
            print("⤴️  Pushing any unpushed commits...")
            run(["git", "push"])
        sys.exit(0)

    # Get a commit message.
    if not message:
        default_msg = f"Update CertPrep Coach ({datetime.now():%Y-%m-%d %H:%M})"
        try:
            entered = input(f"📝 Commit message [{default_msg}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n❌ Cancelled.")
            sys.exit(1)
        message = entered or default_msg

    # Stage everything (respecting .gitignore).
    print("\n➕ Staging changes (git add -A)...")
    code, _ = run(["git", "add", "-A"])
    if code != 0:
        print("❌ 'git add' failed.")
        sys.exit(code)

    # Commit.
    print(f"✅ Committing: \"{message}\"")
    code, _ = run(["git", "commit", "-m", message])
    if code != 0:
        print("❌ 'git commit' failed.")
        sys.exit(code)

    # Push.
    if do_push:
        if not has_remote():
            print("⚠️  No remote configured — skipping push.")
            print("   Add one with: git remote add origin <url>")
            sys.exit(0)
        branch = current_branch()
        print(f"⤴️  Pushing to origin/{branch}...")
        code, _ = run(["git", "push", "-u", "origin", branch])
        if code != 0:
            print("❌ 'git push' failed. If this is the first push, check your "
                  "remote URL and GitHub sign-in.")
            sys.exit(code)
        print("\n🎉 Done — changes committed and pushed!")
    else:
        print("\n✅ Committed locally (push skipped). Run 'git push' when ready.")


if __name__ == "__main__":
    main()
