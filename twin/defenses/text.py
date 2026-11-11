"""Text helpers shared by the defenses. Deliberately independent of eval/ (the scorers there are separate code)."""
import re

URL_RE = re.compile(r"https?://[^\s)\]\"'<>]+", re.I)
MD_LINK_RE = re.compile(r"!?\[([^\]]*)\]\(([^)]*)\)")
HTML_TAG_RE = re.compile(r"<[^>]{1,300}>")
# bare host such as attacker.example/path; not an email domain (no @ or word char before) and TLD from a short list
BARE_DOMAIN_RE = re.compile(
    r"(?<![@\w.-])(?:[a-z0-9-]+\.)+(?:com|org|net|io|dev|ai|example|co|app|xyz|info|me|gg|ly|ru|cn|tk)\b(?:/[^\s]*)?", re.I)
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
SECRET_RES = [re.compile(p) for p in (
    r"sk-[A-Za-z0-9_-]{20,}", r"AKIA[0-9A-Z]{16}", r"xox[abp]-[A-Za-z0-9-]{10,}", r"ghp_[A-Za-z0-9]{30,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----")]


def host_of(url):
    m = re.match(r"https?://([^/:?#\s]+)", url, re.I)
    return (m.group(1) if m else "").lower()


def host_allowed(host, allow):
    host = (host or "").lower()
    return any(host == a or host.endswith("." + a) for a in allow)


def strip_links(text, allow, marker="[link removed]"):
    """Remove markdown links/images, HTML tags and URLs or bare hosts that are not allow-listed.
    Returns (clean_text, number_of_removals)."""
    n = 0

    def md(m):
        nonlocal n
        label, target = m.group(1), m.group(2)
        if m.group(0).startswith("!") or not host_allowed(host_of(target), allow):
            n += 1
            return label if not m.group(0).startswith("!") else marker
        return m.group(0)

    text = MD_LINK_RE.sub(md, text)

    def url(m):
        nonlocal n
        if host_allowed(host_of(m.group(0)), allow):
            return m.group(0)
        n += 1
        return marker

    text = URL_RE.sub(url, text)

    def dom(m):
        nonlocal n
        d = m.group(0).split("/")[0]
        if host_allowed(d, allow):
            return m.group(0)
        n += 1
        return marker

    text = BARE_DOMAIN_RE.sub(dom, text)
    cleaned = HTML_TAG_RE.sub("", text)
    if cleaned != text:
        n += 1
    return cleaned, n


def collapse_controls(text):
    return CONTROL_RE.sub("", text).replace("\r", " ").replace("\n", " ")


def words(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def instruction_text(prompt):
    """The part of the system prompt that is instructions: everything before the person's documents plus the
    rules section onward. The documents themselves (summary, CV) are not secret and are excluded."""
    a = prompt.find("Here are the details of the person")
    b = prompt.find("# Rules")
    head = prompt[:a] if a != -1 else prompt
    tail = prompt[b:] if b != -1 else ""
    return head + "\n" + tail


def shared_run(a_words, b_words, n):
    """True if the two word lists share n consecutive words."""
    if len(a_words) < n or len(b_words) < n:
        return False
    grams = {tuple(b_words[i:i + n]) for i in range(len(b_words) - n + 1)}
    return any(tuple(a_words[i:i + n]) in grams for i in range(len(a_words) - n + 1))


def find_secret(text):
    return next((p.pattern[:12] for p in SECRET_RES if p.search(text)), None)
