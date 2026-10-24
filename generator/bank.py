#!/usr/bin/env python3
"""The private theme bank: new themes whose word lists never appear in public.

Every answer in the public themes.json can be found by hashing its word list,
so new themes live here instead, encrypted to a public key committed in the
repository. Anyone (a Claude Code session, you) can add a theme with only that
public key; only the daily workflow, which holds BANK_PRIVATE_KEY, can read the
bank. The nightly run schedules a bank theme for each new date while unused
ones remain (generate.plan_day) and falls back to the public themes otherwise,
so an empty or unreadable bank never stops a round.

    python generator/bank.py keygen --out ~/metahunt-bank-key.pem   # once
    python generator/bank.py add drafts/lighthouse.json             # validate, test-build, encrypt
    python generator/bank.py check                                  # needs BANK_PRIVATE_KEY
    python generator/bank.py list                                   # needs BANK_PRIVATE_KEY

A draft is one theme in the themes.json format, plus optional fields that make
it read as its own world rather than a reskin:

    "cluephrases":   sentences ending in the answer, "{W}" standing for it,
                     used by the cryptogram, rail fence, drop quote and friends
    "flavors":       {puzzle type key: [oblique lines]} for Hard and Medium
    "easy_flavors":  {puzzle type key: [direct lines]} for Easy
    "meta_flavors" / "easy_meta_flavors": {meta type: [lines]}
    "max_uses":      how many days the theme may run (default 1; each use
                     avoids every answer published by the ones before)

Drafts hold answers in the clear: keep them outside the repository or in the
git-ignored drafts/ folder, and delete them once added.
"""
import argparse
import base64
import datetime as dt
import json
import os
import re
import secrets
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate  # noqa: E402
from deep_mechanisms import BY_KEY  # noqa: E402
from hunt_mechanisms import phrase_answer  # noqa: E402

THEMES_DIR = os.path.join(generate.BANK_DIR, "themes")
PUBLIC_KEY = os.path.join(generate.BANK_DIR, "public_key.pem")
SCHEDULE = os.path.join(generate.BANK_DIR, "schedule.json")
META_TYPES = {"diagonal", "title_diagonal", "mutation", "stowaway", "fitin", "logbook", "initials", "first_letters"}
WORD = re.compile(r"[A-Z]+")


# --------------------------------------------------------------------------
# Encryption: RSA-OAEP wraps a fresh AES-256-GCM key per theme
# --------------------------------------------------------------------------

def _crypto():
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        sys.exit("bank.py needs the 'cryptography' package: pip install cryptography")
    oaep = padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    return serialization, rsa, AESGCM, oaep


def encrypt(theme, public_pem):
    serialization, _, AESGCM, oaep = _crypto()
    pub = serialization.load_pem_public_key(public_pem)
    key, nonce = AESGCM.generate_key(256), secrets.token_bytes(12)
    data = AESGCM(key).encrypt(nonce, json.dumps(theme, ensure_ascii=False).encode(), b"metahunt-bank")
    b64 = lambda b: base64.b64encode(b).decode()
    return {"v": 1, "key": b64(pub.encrypt(key, oaep)), "nonce": b64(nonce), "data": b64(data)}


def decrypt(box, private_pem):
    serialization, _, AESGCM, oaep = _crypto()
    priv = serialization.load_pem_private_key(private_pem, password=None)
    key = priv.decrypt(base64.b64decode(box["key"]), oaep)
    return json.loads(AESGCM(key).decrypt(base64.b64decode(box["nonce"]), base64.b64decode(box["data"]), b"metahunt-bank"))


def _theme_files():
    if not os.path.isdir(THEMES_DIR):
        return []
    return sorted(f for f in os.listdir(THEMES_DIR) if f.endswith(".json"))


def load_into(bank):
    """Fill generate.BANK from disk. Missing key or library: say so and leave the themes empty."""
    if os.path.exists(SCHEDULE):
        with open(SCHEDULE) as f:
            bank["schedule"] = json.load(f)
    files = _theme_files()
    if not files:
        return
    pem = os.environ.get("BANK_PRIVATE_KEY")
    if not pem:
        print("bank: %d themes, but BANK_PRIVATE_KEY isn't set; using public themes" % len(files), file=sys.stderr)
        return
    try:
        _crypto()
    except SystemExit as e:
        print("bank: %s; using public themes" % e, file=sys.stderr)
        return
    for f in files:
        try:
            with open(os.path.join(THEMES_DIR, f)) as fh:
                bank["themes"][f[:-5]] = decrypt(json.load(fh), pem.encode())
        except Exception as e:  # a damaged file only loses that one theme
            print("bank: can't read %s: %s" % (f, e), file=sys.stderr)
    print("bank: %d themes loaded, %d days scheduled" % (len(bank["themes"]), len(bank["schedule"])))


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def problems(theme):
    """Everything wrong with a draft theme, as readable strings (empty means it's fine)."""
    out = []
    need = {"id": str, "name": str, "place": str, "at": str, "crew": str, "intro": str,
            "glyphs": dict, "titles": list, "finals": list, "feeders": list}
    for k, t in need.items():
        if not isinstance(theme.get(k), t):
            out.append("%s is missing or isn't a %s" % (k, t.__name__))
    if out:
        return out
    if any(t["id"] == theme["id"] or t["name"] == theme["name"] for t in generate.THEMES):
        out.append("id or name clashes with a public theme")
    if not all(isinstance(theme["glyphs"].get(k), str) and theme["glyphs"][k] for k in ("dot", "dash")):
        out.append("glyphs needs a 'dot' and a 'dash' symbol")
    finals, feeders, titles = theme["finals"], theme["feeders"], theme["titles"]
    for name, words, lo, hi in (("finals", finals, 4, 9), ("feeders", feeders, 3, 12)):
        bad = [w for w in words if not (isinstance(w, str) and WORD.fullmatch(w) and lo <= len(w) <= hi)]
        if bad:
            out.append("%s must be %d-%d capital letters A-Z: %s" % (name, lo, hi, ", ".join(map(str, bad[:8]))))
        if len(set(words)) != len(words):
            out.append("%s has duplicates" % name)
    if len(finals) < 3:
        out.append("needs at least 3 finals (one per level)")
    if len(feeders) < 30:
        out.append("needs at least 30 feeders (has %d); 40+ gives the metas room" % len(feeders))
    if set(finals) & set(feeders):
        out.append("a word is both a final and a feeder: %s" % ", ".join(sorted(set(finals) & set(feeders))))
    if len(set(titles)) < 10:
        out.append("needs at least 10 distinct titles")
    uses = theme.get("max_uses", 1)
    if not isinstance(uses, int) or not 1 <= uses <= max(1, len(finals) // 3):
        out.append("max_uses must be between 1 and len(finals) // 3 = %d" % max(1, len(finals) // 3))
    for k in theme.get("echoes", {}):
        if k not in finals:
            out.append("echo for %s, which isn't a final" % k)

    phrases = theme.get("cluephrases", [])
    for p in phrases:
        if not re.fullmatch(r"[A-Z ]+\{W\}[A-Z ]*", p or ""):
            out.append("cluephrase must be capitals and spaces with one {W}: %r" % p)
    if not any(o.startswith("cluephrase") for o in out):
        ctx = {"cluephrases": phrases}
        for p in phrases:
            for w in feeders + finals:
                if phrase_answer(p.replace("{W}", w), ctx) != w:
                    out.append("cluephrase reads ambiguously with %s: %r" % (w, p))
                    break
    for field in ("flavors", "easy_flavors"):
        for key, lines in theme.get(field, {}).items():
            if key not in BY_KEY:
                out.append("%s: no puzzle type called %r (known: %s)" % (field, key, ", ".join(sorted(BY_KEY))))
            elif not (isinstance(lines, list) and lines and all(isinstance(x, str) and x for x in lines)):
                out.append("%s[%s] must be a non-empty list of lines" % (field, key))
    for field in ("meta_flavors", "easy_meta_flavors"):
        for key, lines in theme.get(field, {}).items():
            if key not in META_TYPES:
                out.append("%s: no meta called %r (known: %s)" % (field, key, ", ".join(sorted(META_TYPES))))
            elif not (isinstance(lines, list) and lines and all(isinstance(x, str) and x for x in lines)):
                out.append("%s[%s] must be a non-empty list of lines" % (field, key))

    # A final printed anywhere on the page gives the round away.
    shown = [theme["intro"], theme["place"], theme["at"], theme["crew"]] + titles + phrases
    for field in ("flavors", "easy_flavors", "meta_flavors", "easy_meta_flavors"):
        shown += [x for lines in theme.get(field, {}).values() for x in lines]
    letters = re.sub(r"[^A-Z]", "", " ".join(shown).upper())
    for f in finals:
        if f in letters:
            out.append("the final %s appears in text players can see (intro, titles, flavour or cluephrases)" % f)
    for f, echo in theme.get("echoes", {}).items():
        if f in re.sub(r"[^A-Z]", "", echo.upper()):
            out.append("the echo for %s contains it" % f)
    return out


def trial_builds(theme, dates=8):
    """Test-build every level, each final taking a turn as the Hard one. Returns (ok, tried, metas by level)."""
    ok = tried = 0
    metas = {level: {} for level in generate.LEVELS}
    start = dt.date(2030, 1, 1)
    for i in range(dates):
        date = (start + dt.timedelta(days=i)).isoformat()
        final = theme["finals"][i % len(theme["finals"])]
        pick = (theme, final, 1, frozenset())
        tried += 1
        try:
            for level in generate.LEVELS:
                _, sol = generate.build("bank-trial", date, level=level, pick=pick)
                metas[level][sol["metaType"]] = metas[level].get(sol["metaType"], 0) + 1
            ok += 1
        except Exception as e:
            print("  trial %s (final %s) failed: %s" % (date, final, e))
    return ok, tried, metas


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def _inside_repo(path):
    return os.path.realpath(path).startswith(os.path.realpath(generate.ROOT) + os.sep)


def _tracked_or_unignored(path):
    """True if git would commit this file (it isn't ignored)."""
    r = subprocess.run(["git", "-C", generate.ROOT, "check-ignore", "-q", os.path.realpath(path)])
    return r.returncode != 0


def cmd_keygen(args):
    serialization, rsa, _, _ = _crypto()
    if os.path.exists(PUBLIC_KEY) and not args.force:
        sys.exit("%s already exists. Replacing it makes every existing bank theme unreadable; pass --force if you mean it."
                 % os.path.relpath(PUBLIC_KEY, generate.ROOT))
    if _inside_repo(args.out):
        sys.exit("Write the private key outside the repository, so it can never be committed.")
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    with open(os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as f:
        f.write(pem)
    os.makedirs(generate.BANK_DIR, exist_ok=True)
    with open(PUBLIC_KEY, "wb") as f:
        f.write(key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    print("Public key:  %s (commit this)" % os.path.relpath(PUBLIC_KEY, generate.ROOT))
    print("Private key: %s" % args.out)
    print("Paste the whole private key file into a repository Actions secret named BANK_PRIVATE_KEY,\n"
          "keep a copy somewhere safe, and delete this file. Lose it and the bank can't be read.")


def cmd_add(args):
    if not os.path.exists(PUBLIC_KEY) and not args.dry_run:
        sys.exit("No public key yet: run 'python generator/bank.py keygen --out <path outside the repo>' first.")
    with open(args.draft) as f:
        theme = json.load(f)
    if _inside_repo(args.draft) and _tracked_or_unignored(args.draft):
        sys.exit("%s is inside the repository and not git-ignored, so its answers could get committed. "
                 "Move it to drafts/ (ignored) or outside the repo." % args.draft)
    errs = problems(theme)
    if errs:
        sys.exit("Not added:\n  - " + "\n  - ".join(errs))
    ok, tried, metas = trial_builds(theme)
    print("Trial builds: %d/%d dates built all three levels" % (ok, tried))
    for level, m in metas.items():
        print("  %-6s metas: %s" % (level, ", ".join("%s x%d" % kv for kv in sorted(m.items())) or "none"))
    if ok < tried:
        sys.exit("Not added: every trial must build. Usually the fix is more feeders, or feeders that share "
                 "more letters with the finals.")
    if args.dry_run:
        print("Dry run: looks good, nothing written.")
        return
    with open(PUBLIC_KEY, "rb") as f:
        box = encrypt(theme, f.read())
    tid = secrets.token_hex(4)  # opaque, so file names don't announce what's coming
    generate.write_json(os.path.join(THEMES_DIR, tid + ".json"), box)
    print("Added %s as generator/bank/themes/%s.json. Now delete the draft." % (theme["name"], tid))


def _need_key():
    if not os.environ.get("BANK_PRIVATE_KEY"):
        sys.exit("Set BANK_PRIVATE_KEY (the private key's PEM text) to read the bank.")
    generate.BANK.update({"themes": {}, "schedule": {}})
    load_into(generate.BANK)
    return generate.BANK


def cmd_list(args):
    bank = _need_key()
    for tid, t in sorted(bank["themes"].items(), key=lambda kv: kv[1]["name"]):
        days = sorted(d for d, e in bank["schedule"].items() if e["theme"] == tid)
        print("%s  %-36s uses %d/%d  %s" % (tid, t["name"], len(days), t.get("max_uses", 1), " ".join(days)))
    left = sum(t.get("max_uses", 1) - sum(e["theme"] == tid for e in bank["schedule"].values())
               for tid, t in bank["themes"].items())
    print("%d themes, about %d days of rounds left" % (len(bank["themes"]), left))


def cmd_check(args):
    bank = _need_key()
    bad = 0
    for tid, t in sorted(bank["themes"].items()):
        errs = problems(t)
        ok, tried, _ = trial_builds(t, dates=4)
        status = "ok" if not errs and ok == tried else "PROBLEM"
        bad += status != "ok"
        print("%s %-36s %s (%d/%d trial builds)" % (tid, t["name"], status, ok, tried))
        for e in errs:
            print("    - " + e)
    sys.exit(1 if bad else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keygen", help="make the bank's key pair (once)")
    k.add_argument("--out", required=True, help="where to write the private key (outside the repo)")
    k.add_argument("--force", action="store_true")
    a = sub.add_parser("add", help="validate, test-build and encrypt a draft theme into the bank")
    a.add_argument("draft")
    a.add_argument("--dry-run", action="store_true", help="validate and test-build only")
    sub.add_parser("list", help="themes in the bank and when they ran (needs BANK_PRIVATE_KEY)")
    sub.add_parser("check", help="re-validate every bank theme (needs BANK_PRIVATE_KEY)")
    args = ap.parse_args()
    {"keygen": cmd_keygen, "add": cmd_add, "list": cmd_list, "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    main()
