"""Deterministic, tagged-PDF generator for Kopilotti Sales overview PDFs.

Produces four validated outputs: FI/EN landscape 4:3 LinkedIn carousels and
FI/EN A4 documents built from the approved Markdown sources. All outputs are
genuinely tagged for accessibility.

Rendering engine
-----------------
ReportLab's Canvas API has no supported way to emit a real PDF structure
tree (/StructTreeRoot, /MarkInfo, typed /H1 /P /L /LI /Link structure
elements) - confirmed by inspecting reportlab 5.0.1's source. fpdf2 2.8.8's
only wired-up struct type for text content is "/Figure" (misapplied even to
headings) - not a safe way to produce correct tags either. So this script
renders semantic HTML through a local headless Chrome/Chromium's
--print-to-pdf, which has genuinely correct PDF tagging as part of its
accessibility export.

Fail-closed generation (this revision)
---------------------------------------
An earlier revision of this script only checked Chrome's process existence
and exit code, and reused the old final PDF's hashes as "success" if
generation silently produced nothing new. A second independent review
proved this concretely (a fabricated "Chromium 90" stub emitting a 1-page,
untagged, wrong-size PDF was accepted; a killed Chrome process left a
partial file in docs/; a failed run reported stale hashes as success). This
revision replaces that with a transactional pipeline (see generate_validated
and main): Chrome always writes to a fresh, uniquely-named temp file that
must not exist beforehand; the raw output is opened with a PDF parser and
validated (page count, page size, /Lang, /MarkInfo, /StructTreeRoot,
/ParentTree, required structure-element counts, 10 OBJR-bound links, a
per-page text fingerprint against the exact guard-approved content, absence
of dangerous PDF actions, absence of leftover Markdown syntax) *before* the
pikepdf metadata normalization step, and re-validated *after* it. Only then
are both languages' validated temp files atomically swapped into place
together (os.replace, same filesystem as the destination) - if either
language fails validation at any point, neither final file is touched, no
"success" hashes are printed, and all temp files are removed. A Chrome
capability probe (verify_chrome_capability) runs once before any real
document is generated, checking not just `--version` output but that the
browser actually produces genuinely tagged output for a small known-content
probe document - a browser/stub that can't do this is rejected before it
ever touches the real content.

Inline-Markdown-to-HTML (this revision)
-----------------------------------------
An earlier revision embedded SourceGuard's raw source text (which may
contain literal backticks, e.g. `` `ACCEPT` ``) directly into the rendered
HTML, escaped but unconverted - so raw Markdown syntax was visible in the
shipped PDF. render_inline_markdown() now converts *only* a small allowed
subset of inline Markdown (code spans, **strong**, _emphasis_/*emphasis*,
and `[link text](url)` -> the link's visible text) into safe, HTML-escaped
markup, and raises on anything else (unmatched delimiters, raw HTML angle
brackets, unrecognized syntax) rather than silently passing it through or
guessing.

Source-of-truth binding (fail-closed)
--------------------------------------
Every sales claim bullet is looked up live from docs/kopilotti-sales-
overview-{fi,en}.md's `<!-- sales-claim id="..." status="..." -->` markers
(SourceGuard.assert_claim), which asserts the hardcoded visible text still
matches the source's text and evidence class exactly. Framing/quote/caveat
text is checked with SourceGuard.assert_verbatim, which (this revision)
requires an exact, in-order run of whole source *sentences* inside a single
source file - not a substring match anywhere in a blob of the whole
corpus - so truncating a hedge clause, dropping a negation, or splicing
unrelated fragments together no longer passes. Section headers that convey
an evidence class to the reader (previously unchecked) are now bound via
SourceGuard.assert_evidence_header, which requires a class-specific marker
phrase and forbids the other classes' marker phrases, per language, so a
header can't be silently reclassified (e.g. "not production-verified" ->
"production-ready").

See scripts/test_source_guard_canaries.py for canaries covering the original
failure modes, and the additional canaries this revision adds inline where
noted.

System dependency
------------------
Requires a local Chromium-family browser with `--headless --print-to-pdf`
tagged-PDF support, verified via a structural capability probe at runtime
(not just a version string), plus `pdftotext` (poppler) for per-page text
extraction during output validation. Neither is pip-installable; see
scripts/requirements-docs.txt for what *is* pinned (pikepdf) and for the
documented system-dependency versions this was verified against.
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pikepdf

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
OUT_DIR = DOCS_DIR

PAGE_W_PT, PAGE_H_PT = 960, 720  # 4:3 landscape
REPO = "https://github.com/mikko-lab/kopilotti-sales-demo"
DEMO_URL = "https://app.kopilotti.online"
FIXED_DATE = "D:20000101000000+00'00'"


class GenerationError(Exception):
    """Any fail-closed abort of the generation pipeline."""


# --- inline-Markdown -> safe HTML (P1.1) ------------------------------------
#
# Only these four constructs are recognized: code spans, **strong**,
# _em_/*em* emphasis, and [text](url) (only the visible text is kept - this
# generator never embeds arbitrary URLs found in source prose; all real
# hyperlinks come from the explicit, guard-approved links pages). Everything
# else - unmatched delimiters, raw `<`/`>`, unrecognized syntax - raises.

_CODE_OR_STRONG_RE = re.compile(r"`([^`\n]+)`|\*\*([^*\n]+)\*\*")
_MD_LINK_RE = re.compile(r"\[([^\]\n]*)\]\(([^)\n]*)\)")
_UNDERSCORE_EM_RE = re.compile(r"(?<!\w)_(?!\s)([^_\n]+?)(?<!\s)_(?!\w)")
_SINGLE_ASTERISK_EM_RE = re.compile(r"(?<!\*)\*(?!\s)([^*\n]+?)(?<!\s)\*(?!\*)")


def esc(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_inline_markdown(raw):
    if "<" in raw or ">" in raw:
        raise GenerationError(f"unsupported raw HTML/angle-bracket content in: {raw!r}")

    # Resolve markdown links to their visible text first (recursively run
    # through the same restricted renderer, so a link label may itself use
    # code/strong/emphasis, but not another link).
    def link_sub(m):
        label = m.group(1)
        if "[" in label or "]" in label:
            raise GenerationError(f"unsupported nested markdown link in: {raw!r}")
        return render_inline_markdown(label)

    working = _MD_LINK_RE.sub(lambda m: "\x00" + link_sub(m) + "\x00", raw)

    out = []
    pos = 0
    for m in _CODE_OR_STRONG_RE.finditer(working):
        out.append(_finish_plain(working[pos : m.start()]))
        if m.group(1) is not None:
            out.append(f"<code>{esc(m.group(1))}</code>")
        else:
            out.append(f"<strong>{esc(m.group(2))}</strong>")
        pos = m.end()
    out.append(_finish_plain(working[pos:]))
    rendered = "".join(out)
    return rendered.replace("\x00", "")


def _finish_plain(segment):
    """Handle emphasis + reject leftover markdown delimiters in a segment
    that contains no code/strong spans (those were already extracted by the
    caller)."""
    if "`" in segment or "**" in segment:
        raise GenerationError(f"unmatched/unsupported markdown delimiter near: {segment!r}")
    if "[" in segment or "]" in segment:
        # Any '[' or ']' still present here was not consumed by _MD_LINK_RE
        # (which already ran over the whole string before code/strong
        # extraction) - so it is either an unmatched bracket or a Markdown
        # construct this renderer does not support (e.g. reference-style
        # [text][ref] links). Fail closed rather than let raw bracket/link
        # syntax leak into the rendered PDF.
        raise GenerationError(f"unsupported/unmatched markdown bracket near: {segment!r}")

    out = []
    pos = 0
    combined = re.compile(
        f"(?:{_UNDERSCORE_EM_RE.pattern})|(?:{_SINGLE_ASTERISK_EM_RE.pattern})"
    )
    for m in combined.finditer(segment):
        out.append(esc(segment[pos : m.start()]))
        content = m.group(1) if m.group(1) is not None else m.group(2)
        out.append(f"<em>{esc(content)}</em>")
        pos = m.end()
    tail = segment[pos:]
    if "_" in tail:
        # A lone/unmatched underscore outside a recognized emphasis span.
        # Underscores inside ordinary words (snake_case-free in this
        # content) are not expected; fail closed rather than guess.
        if re.search(r"(?<!\w)_|_(?!\w)", tail):
            raise GenerationError(f"unmatched/unsupported underscore-emphasis near: {segment!r}")
    if re.search(r"(?<!\*)\*(?!\*)", tail):
        raise GenerationError(f"unmatched/unsupported single-asterisk emphasis near: {segment!r}")
    out.append(esc(tail))
    return "".join(out)


# --- comparison normalization + sentence splitting (P2.2) ------------------


_LEADING_MARKDOWN_MARKER_RE = re.compile(r"(?m)^\s*(?:>+\s*|-\s+|\d+\.\s+)")


def normalize(text):
    """Strip only meaningless markdown *presentation* (leading blockquote
    '>', bullet '-', or numbered-list 'N.' markers; backticks; **) and
    collapse whitespace. Must never remove negation, modality, safety
    hedges, or punctuation that would splice separate sentences together.

    The leading-marker strip must run line-by-line (MULTILINE, before
    whitespace collapsing folds newlines away) - otherwise every source
    sentence that happens to start a markdown list item or blockquote line
    would carry that marker as part of the "sentence" text, and a generator
    string with the same words but no marker would never match it exactly
    under the strict sentence-sequence comparison in assert_verbatim."""
    text = _LEADING_MARKDOWN_MARKER_RE.sub("", text)
    text = text.replace("`", "").replace("**", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")


def split_sentences(normalized_text):
    parts = _SENTENCE_SPLIT_RE.split(normalized_text)
    return [p.strip() for p in parts if p.strip()]


def paragraph_sentence_lists(raw_text):
    """Split raw source text into paragraphs (blank-line separated) *before*
    normalizing/sentence-splitting each one independently, and keep each
    paragraph's sentence list separate rather than merging them into one big
    haystack.

    This matters because a markdown heading line ("# Kopilotti Sales -
    tuote-esittely") has no terminal '.'/'!'/'?' - so on a single flattened
    haystack, split_sentences would silently fuse it with the *next*
    paragraph's first sentence into one "sentence" that never matches the
    plain tagline text. Paragraph boundaries are a hard stop regardless of
    whether the preceding paragraph ends in terminal punctuation, which also
    strengthens same-file cross-section matching: two sentences can only be
    treated as adjacent if they were adjacent within one source paragraph."""
    paragraphs = _PARAGRAPH_SPLIT_RE.split(raw_text)
    result = []
    for para in paragraphs:
        sentences = split_sentences(normalize(para))
        if sentences:
            result.append(sentences)
    return result


CLAIM_RE = re.compile(
    r'<!--\s*sales-claim\s+id="([^"]+)"\s+status="([^"]+)"\s*-->\s*\n-\s*(.+)'
)


def load_claims(md_path):
    text = md_path.read_text(encoding="utf-8")
    claims = {}
    for m in CLAIM_RE.finditer(text):
        claim_id, status, bullet = m.group(1), m.group(2), m.group(3).strip()
        if claim_id in claims:
            raise ValueError(f"duplicate sales-claim id {claim_id!r} in {md_path}")
        claims[claim_id] = {"status": status, "text": bullet}
    if not claims:
        raise ValueError(f"no sales-claim markers found in {md_path} (unexpected)")
    return claims


# --- evidence-class header binding (P2.1) -----------------------------------
#
# required: at least one of these (case-insensitive) must appear in the
#           header text.
# forbidden: none of the *other* classes' markers may appear - this is what
#            actually blocks reclassification ("not production-verified" ->
#            "production-ready", "roadmap" -> "implemented").

EVIDENCE_HEADER_MARKERS = {
    "prodverified": {
        "fi": {
            "required": ["rajatusti tuotantovarmennettu", "rajattu tuotantovarmennus"],
            "forbidden": ["toteutettu ja testattu", "ei tuotantovarmennettu", "not production-verified", "roadmap", "tutkimussuunt"],
        },
        "en": {
            "required": ["production-verified scope", "limited production verification"],
            "forbidden": ["implemented and tested", "not production-verified", "roadmap", "research direction"],
        },
    },
    "tested": {
        "fi": {
            "required": ["toteutettu ja testattu"],
            "forbidden": ["rajatusti tuotantovarmennettu", "rajattu tuotantovarmennus", "ei tuotantovarmennettu", "not production-verified", "roadmap", "tutkimussuunt"],
        },
        "en": {
            "required": ["implemented and tested"],
            "forbidden": ["production-verified scope", "limited production verification", "not production-verified", "roadmap", "research direction"],
        },
    },
    "notprod": {
        # FI accepts both the Finnish phrase used on the page headers and the
        # literal English term retained in status identifiers and guard tests.
        "fi": {
            "required": ["ei tuotantovarmennettu", "not production-verified"],
            "forbidden": ["rajatusti tuotantovarmennettu", "rajattu tuotantovarmennus", "toteutettu ja testattu", "roadmap", "tutkimussuunt"],
        },
        "en": {
            "required": ["not production-verified"],
            "forbidden": ["production-verified scope", "limited production verification", "implemented and tested", "roadmap", "research direction"],
        },
    },
    "roadmap": {
        "fi": {
            "required": ["roadmap", "tutkimussuunt"],
            "forbidden": ["rajatusti tuotantovarmennettu", "rajattu tuotantovarmennus", "toteutettu ja testattu", "ei tuotantovarmennettu", "not production-verified"],
        },
        "en": {
            "required": ["roadmap", "research direction"],
            "forbidden": ["production-verified scope", "limited production verification", "implemented and tested", "not production-verified"],
        },
    },
}


class SourceGuard:
    """Fail-closed binding of every rendered sentence/claim/header to the
    approved sources."""

    def __init__(self, docs_dir=DOCS_DIR, root=ROOT):
        self.claims = {
            "fi": load_claims(docs_dir / "kopilotti-sales-overview-fi.md"),
            "en": load_claims(docs_dir / "kopilotti-sales-overview-en.md"),
        }
        fi_ids, en_ids = set(self.claims["fi"]), set(self.claims["en"])
        if fi_ids != en_ids:
            raise ValueError(
                "FI/EN sales-claim id sets differ: "
                f"only-FI={fi_ids - en_ids} only-EN={en_ids - fi_ids}"
            )

        # Kept as separate per-paragraph sentence lists (not one merged
        # blob, not even one list per file) so a match can never be
        # assembled by splicing the tail of one paragraph/file to the head
        # of another - see paragraph_sentence_lists' docstring.
        self.sentence_sources = {
            "fi": (
                paragraph_sentence_lists((docs_dir / "kopilotti-sales-overview-fi.md").read_text(encoding="utf-8"))
                + paragraph_sentence_lists((root / "README.md").read_text(encoding="utf-8"))
            ),
            "en": (
                paragraph_sentence_lists((docs_dir / "kopilotti-sales-overview-en.md").read_text(encoding="utf-8"))
                + paragraph_sentence_lists((root / "README.en.md").read_text(encoding="utf-8"))
            ),
        }
        self._used_ids = set()

    def assert_claim(self, lang, claim_id, expected_status, expected_text):
        table = self.claims[lang]
        if claim_id not in table:
            raise ValueError(f"unknown sales-claim id {claim_id!r} for lang={lang!r}")
        if claim_id in self._used_ids and lang == "fi":
            raise ValueError(f"sales-claim id {claim_id!r} used more than once in this document")
        self._used_ids.add(claim_id)
        entry = table[claim_id]
        if entry["status"] != expected_status:
            raise ValueError(
                f"sales-claim {claim_id!r} ({lang}) status mismatch: "
                f"generator expects {expected_status!r}, source says {entry['status']!r}"
            )
        if normalize(entry["text"]) != normalize(expected_text):
            raise ValueError(
                f"sales-claim {claim_id!r} ({lang}) visible text does not match source.\n"
                f"  generator text: {expected_text!r}\n"
                f"  source text:    {entry['text']!r}"
            )
        return entry["text"]

    def assert_verbatim(self, lang, text):
        """Require an exact, in-order run of whole source sentences inside a
        single approved source file - not a substring match against a blob
        of the whole corpus. Truncating a hedge, dropping a negation,
        splicing unrelated sentences together, or reordering all fail this."""
        needle = split_sentences(normalize(text))
        if not needle:
            raise ValueError(f"empty framing text: {text!r}")
        n = len(needle)
        for haystack in self.sentence_sources[lang]:
            for i in range(len(haystack) - n + 1):
                if haystack[i : i + n] == needle:
                    return text
        raise ValueError(
            f"framing text not found as an exact, in-order sentence match in a single "
            f"approved {lang} source file: {text!r}"
        )

    def assert_evidence_header(self, lang, evidence_class, header_text):
        rules = EVIDENCE_HEADER_MARKERS[evidence_class][lang]
        lowered = header_text.lower()
        if not any(marker.lower() in lowered for marker in rules["required"]):
            raise ValueError(
                f"header for evidence class {evidence_class!r} ({lang}) is missing a required "
                f"marker {rules['required']!r}: {header_text!r}"
            )
        for marker in rules["forbidden"]:
            if marker.lower() in lowered:
                raise ValueError(
                    f"header for evidence class {evidence_class!r} ({lang}) contains a marker "
                    f"belonging to a different evidence class ({marker!r}): {header_text!r}"
                )
        return header_text

    def assert_section_binding(self, lang, evidence_class, header_text, claim_status):
        """Bind a visible section header to the *same* evidence class as the
        claims rendered under it. assert_evidence_header alone only checks
        that a header's wording matches one evidence class's marker phrases
        in isolation - it does not know what status the claims placed under
        that header actually carry. Two independently-correct calls
        (assert_evidence_header for the header, assert_claim per bullet for
        the claims) can still drift apart - e.g. a future edit pastes the
        "tested" header text onto a section whose bullets are still asserted
        against notprod/roadmap status - and neither call alone would catch
        that. This method requires the header's evidence_class and the
        section's claim status to agree with the same canonical mapping."""
        self.assert_evidence_header(lang, evidence_class, header_text)
        expected_status = STATUS_FOR_EVIDENCE_CLASS[evidence_class]
        if claim_status != expected_status:
            raise ValueError(
                f"section header/claim status conflict ({lang}): header is bound to evidence "
                f"class {evidence_class!r} (status {expected_status!r}) but the claims rendered "
                f"under it were asserted against status {claim_status!r}: {header_text!r}"
            )
        return header_text


STATUS_FOR_EVIDENCE_CLASS = {
    "prodverified": "production-verified-scope",
    "tested": "implemented-tested",
    "notprod": "implemented-not-production-verified",
    "roadmap": "roadmap-research",
}


# --- claim-ID-bound content, in the order rendered -------------------------

TESTED_IDS = [
    "digital-price-negotiation",
    "llm-isolated-commercial-decision",
    "deterministic-decision-engine",
    "dealer-commercial-boundaries-price-floor",
    "deterministic-canonicalization-hashes",
    "safe-local-receipt-link-boundary",
]
PRODVERIFIED_IDS = [
    "postgres-session-persistence",
    "tenant-scoped-negotiation-session-access",
    "database-enforced-tenant-relationship-integrity",
    "readiness-schema-verification-gates",
    "verified-backup-restore",
]
NOTPROD_IDS = [
    "atomic-vehicle-reservation",
    "database-enforced-double-booking-prevention",
    "application-audit-history-hash-chain",
    "append-only-audit-application-path",
]
ROADMAP_IDS_1 = [
    "live-ddn-verification",
    "signer-authentication-trust-profiles",
    "quorum-public-anchoring",
    "independent-offline-verifier",
    "byte-exact-runtime-replay",
    "signed-committed-decision-artifact",
]
ROADMAP_IDS_2 = [
    "proof-gated-execution",
    "zero-knowledge-proofs",
    "approved-rto-rpo-targets",
    "named-operational-owners-response-times",
]

TEXT = {
    "fi": {
        "prodverified": {
            "postgres-session-persistence": "neuvottelusessioiden pysyvä PostgreSQL-tallennus tuotannossa",
            "tenant-scoped-negotiation-session-access": "tenant-rajattu neuvottelusession käyttö",
            "database-enforced-tenant-relationship-integrity": "tenant-suhteiden tietokantatason eheys",
            "readiness-schema-verification-gates": "tuotannon skeema- ja readiness-portit",
            "verified-backup-restore": "ennen julkaisua läpäisty backup/restore-testi",
        },
        "tested": {
            "digital-price-negotiation": "digitaalinen hintaneuvottelu",
            "llm-isolated-commercial-decision": "LLM:stä erotettu palvelinpuolen kaupallinen päätös",
            "deterministic-decision-engine": "deterministinen ACCEPT-, COUNTER-, REJECT- ja ESCALATE-logiikka",
            "dealer-commercial-boundaries-price-floor": "jälleenmyyjän määrittämät kaupalliset rajat ja hintalattian noudattaminen",
            "deterministic-canonicalization-hashes": "deterministinen kanonisointi ja hashien muodostus",
            "safe-local-receipt-link-boundary": "turvallisen kuittilinkin paikallinen muodostus- ja näyttöraja",
        },
        "notprod": {
            "atomic-vehicle-reservation": "atominen ajoneuvon varaus",
            "database-enforced-double-booking-prevention": "tietokantarajoitteeseen perustuva aktiivisten tuplavarausten esto",
            "application-audit-history-hash-chain": "sovelluksen auditointihistoria ja hash-ketju",
            "append-only-audit-application-path": "auditointitapahtumien append-only-sovelluspolku",
        },
        "roadmap": {
            "live-ddn-verification": "live DDN -varmennus",
            "signer-authentication-trust-profiles": "allekirjoittajan autentikointi ja kiinnitetyt trust profile -määritykset",
            "quorum-public-anchoring": "quorum-varmennus ja julkinen ankkurointi",
            "independent-offline-verifier": "riippumaton offline-varmennin",
            "byte-exact-runtime-replay": "byte-exact runtime replay",
            "signed-committed-decision-artifact": "allekirjoitettu committed decision artifact",
            "proof-gated-execution": "proof-gated execution",
            "zero-knowledge-proofs": "zero-knowledge proofs",
            "approved-rto-rpo-targets": "hyväksytyt RTO/RPO-tavoitteet",
            "named-operational-owners-response-times": "nimetyt operatiiviset omistajat ja vasteajat",
        },
        "title": "Kopilotti Sales",
        "tagline": "Kopilotti Sales digitalisoi käytetyn ajoneuvon hintaneuvottelun.",
        "quote": "LLM keskustelee. Backend päättää.",
        "policy": "Jälleenmyyjä määrittää säännöt. Järjestelmä soveltaa niitä johdonmukaisesti.",
        "status_core": "Tila: rajattu tuotantovarmennus 26.8.2026.",
        "status_suffix": " — ks. rajaus.",
        "cta": "Kokeile demoa",
        "how_header": "Miten Kopilotti Sales toimii",
        "how_bullets": [
            "Asiakas avaa ajoneuvokohtaisen neuvottelupolun.",
            "Asiakas lähettää tarjouksen.",
            "Palvelin lataa ajoneuvon ja voimassa olevan kaupallisen politiikan.",
            "Sääntömoottori palauttaa tuloksen ACCEPT, COUNTER, REJECT tai ESCALATE.",
            "Hyväksytty tulos voi varata ajoneuvon samassa tietokantatransaktiossa päätöksen, session tilasiirtymän ja auditointitapahtuman kanssa.",
            "Asiakas jatkaa jälleenmyyjän omassa viimeistelyprosessissa, tai eskaloitu tapaus siirtyy ihmiselle.",
        ],
        "prodverified_header": "Rajatusti tuotantovarmennettu 26.8.2026",
        "prodverified_caveat": "Varmennus koskee vain yllä kuvattua rajattua tuotantolaajuutta.",
        "tested_header": "Toteutettu ja testattu",
        "notprod_header": "Rakennettu ja testattu, ei tuotantovarmennettu",
        "notprod_caveat": "Varaus- ja auditointimekanismit on toteutettu ja testattu, mutta niitä ei ole tässä yhteydessä tuotantovarmennettu.",
        "roadmap1_header": "Roadmap ja tutkimussuunnat (1/2)",
        "roadmap2_header": "Roadmap ja tutkimussuunnat (2/2)",
        "roadmap_caveat": "Nämä ovat tavoite- tai tutkimussuuntia, eivät nykyisiä ominaisuuksia.",
        "security_header": "Turvallisuusrajat",
        "security_bullets": [
            "LLM voi tukea keskustelua, mutta ei päätä hintaa tai kaupallista tulosta.",
            "LLM-eristys pienentää manipulaation vaikutusta, mutta ei ole lupaus täydellisestä prompt injection -suojasta.",
            "Hash osoittaa eheyteen liittyvää johdonmukaisuutta, ei kuitin antajan identiteettiä tai luottamusketjua.",
            "Roadmap-ominaisuuksia ei käytetä nykyisen päätöksenteon edellytyksenä.",
            "Tämä esittely ei valtuuta deployta, migraatioita tai tuotantopalveluiden käyttöä.",
        ],
        "links1_header": "Lisätietoja (1/2)",
        "links1": [
            ("Demo", DEMO_URL),
            ("Julkinen repository", REPO),
            ("Suomenkielinen Markdown", f"{REPO}/blob/main/docs/kopilotti-sales-overview-fi.md"),
            ("Englanninkielinen Markdown", f"{REPO}/blob/main/docs/kopilotti-sales-overview-en.md"),
            ("Suomenkielinen PDF", f"{REPO}/blob/main/docs/kopilotti-sales-overview-fi.pdf"),
        ],
        "links2_header": "Lisätietoja (2/2)",
        "links2": [
            ("Englanninkielinen PDF", f"{REPO}/blob/main/docs/kopilotti-sales-overview-en.pdf"),
            ("Suomenkielinen README", f"{REPO}/blob/main/README.md"),
            ("Englanninkielinen README", f"{REPO}/blob/main/README.en.md"),
            ("License", f"{REPO}/blob/main/LICENSE"),
        ],
        "footer_brand": "Kopilotti Sales — rajattu tuotantovarmennus",
        "pdf_title": "Kopilotti Sales - tuote-esittely (LinkedIn)",
        "pdf_subject": "Yritysneutraali suomenkielinen tuote-esittely - LinkedIn-optimoitu versio",
    },
    "en": {
        "prodverified": {
            "postgres-session-persistence": "durable PostgreSQL storage of negotiation sessions in production",
            "tenant-scoped-negotiation-session-access": "tenant-scoped negotiation-session access",
            "database-enforced-tenant-relationship-integrity": "database-enforced integrity for tenant relationships",
            "readiness-schema-verification-gates": "production schema and readiness gates",
            "verified-backup-restore": "backup-and-restore test passed before release",
        },
        "tested": {
            "digital-price-negotiation": "digital price negotiation",
            "llm-isolated-commercial-decision": "a server-side commercial decision isolated from the LLM",
            "deterministic-decision-engine": "deterministic ACCEPT, COUNTER, REJECT, and ESCALATE logic",
            "dealer-commercial-boundaries-price-floor": "dealer-defined commercial boundaries and price-floor enforcement",
            "deterministic-canonicalization-hashes": "deterministic canonicalization and hash generation",
            "safe-local-receipt-link-boundary": "a safe local boundary for constructing and displaying a receipt link",
        },
        "notprod": {
            "atomic-vehicle-reservation": "atomic vehicle reservation",
            "database-enforced-double-booking-prevention": "database-enforced prevention of concurrent active reservations",
            "application-audit-history-hash-chain": "application audit history and hash chain",
            "append-only-audit-application-path": "append-only application path for audit events",
        },
        "roadmap": {
            "live-ddn-verification": "live DDN verification",
            "signer-authentication-trust-profiles": "signer authentication and pinned trust profiles",
            "quorum-public-anchoring": "quorum verification and public anchoring",
            "independent-offline-verifier": "an independent offline verifier",
            "byte-exact-runtime-replay": "byte-exact runtime replay",
            "signed-committed-decision-artifact": "a signed committed decision artifact",
            "proof-gated-execution": "proof-gated execution",
            "zero-knowledge-proofs": "zero-knowledge proofs",
            "approved-rto-rpo-targets": "approved RTO/RPO targets",
            "named-operational-owners-response-times": "named operational owners and response times",
        },
        "title": "Kopilotti Sales",
        "tagline": "Kopilotti Sales digitizes used-vehicle price negotiation.",
        "quote": "The LLM converses. The backend decides.",
        "policy": "The dealer defines the policy. The system applies it consistently.",
        "status_core": "Status: limited production verification completed on 26 August 2026.",
        "status_suffix": " — see scope.",
        "cta": "Try the demo",
        "how_header": "How Kopilotti Sales works",
        "how_bullets": [
            "The customer opens a vehicle-specific negotiation flow.",
            "The customer submits an offer.",
            "The server loads the vehicle and the applicable commercial policy.",
            "The policy engine returns ACCEPT, COUNTER, REJECT, or ESCALATE.",
            "An accepted outcome may reserve the vehicle in the same database transaction as the decision, session transition, and audit event.",
            "The customer continues in the dealer's own completion process, or a person handles an escalated case.",
        ],
        "prodverified_header": "Production-verified scope - 26 August 2026",
        "prodverified_caveat": "The verification applies only to the limited production scope listed above.",
        "tested_header": "Implemented and tested",
        "notprod_header": "Built and tested, not production-verified",
        "notprod_caveat": "Reservation and audit mechanisms are implemented and tested but have not been production-verified in this review.",
        "roadmap1_header": "Roadmap and research directions (1/2)",
        "roadmap2_header": "Roadmap and research directions (2/2)",
        "roadmap_caveat": "These are target or research directions, not current capabilities.",
        "security_header": "Security boundaries",
        "security_bullets": [
            "The LLM may support conversation but does not decide the price or commercial outcome.",
            "LLM isolation reduces the impact of manipulation but is not a promise of complete prompt-injection protection.",
            "A hash shows integrity-related consistency, not issuer identity or a trust chain.",
            "Roadmap capabilities are not prerequisites for the current decision flow.",
            "This overview does not authorize deployment, migrations, or access to production services.",
        ],
        "links1_header": "Further information (1/2)",
        "links1": [
            ("Demo", DEMO_URL),
            ("Public repository", REPO),
            ("Finnish Markdown", f"{REPO}/blob/main/docs/kopilotti-sales-overview-fi.md"),
            ("English Markdown", f"{REPO}/blob/main/docs/kopilotti-sales-overview-en.md"),
            ("Finnish PDF", f"{REPO}/blob/main/docs/kopilotti-sales-overview-fi.pdf"),
        ],
        "links2_header": "Further information (2/2)",
        "links2": [
            ("English PDF", f"{REPO}/blob/main/docs/kopilotti-sales-overview-en.pdf"),
            ("Finnish README", f"{REPO}/blob/main/README.md"),
            ("English README", f"{REPO}/blob/main/README.en.md"),
            ("License", f"{REPO}/blob/main/LICENSE"),
        ],
        "footer_brand": "Kopilotti Sales — limited production verification",
        "pdf_title": "Kopilotti Sales - product overview (LinkedIn)",
        "pdf_subject": "Company-neutral English product overview - LinkedIn-optimized version",
    },
}

TOTAL_PAGES = 10

PAGE_CSS = f"""
@page {{ size: {PAGE_W_PT}pt {PAGE_H_PT}pt; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  font-family: Helvetica, Arial, sans-serif;
  color: #000;
  -webkit-print-color-adjust: exact;
}}
section.page {{
  position: relative;
  width: {PAGE_W_PT}pt;
  height: {PAGE_H_PT}pt;
  padding: 56pt 64pt;
  break-after: page;
  display: flex;
  flex-direction: column;
}}
section.page:last-child {{ break-after: auto; }}
h1 {{ font-size: 32pt; margin: 0 0 8pt 0; }}
.title h1 {{ font-size: 36pt; }}
.tagline {{ font-size: 24pt; margin: 0 0 20pt 0; }}
.content {{
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}}
.title .content {{
  justify-content: flex-start;
  padding-top: 24pt;
}}
ul.bullets {{
  list-style: disc;
  padding-left: 26pt;
  margin: 0;
}}
ul.bullets li {{
  font-size: 22pt;
  line-height: 1.5;
  margin: 0 0 20pt 0;
}}
ul.bullets li:last-child {{ margin-bottom: 0; }}
code {{ font-family: "Courier New", monospace; font-size: 0.92em; }}
p.caveat {{ font-size: 14pt; color: #444; margin: 18pt 0 0 0; }}
a {{ color: #1c59d9; text-decoration: underline; }}
p.cta {{ font-size: 24pt; font-weight: bold; margin: 24pt 0 0 0; }}
ul.links {{ list-style: none; padding: 0; margin: 0; }}
ul.links li {{ font-size: 22pt; margin: 0 0 22pt 0; }}
ul.links li .url {{ display: block; font-size: 18pt; font-weight: normal; margin-top: 4pt; }}
footer {{
  position: absolute;
  left: 64pt;
  right: 64pt;
  bottom: 24pt;
  display: flex;
  justify-content: space-between;
  font-size: 12pt;
  color: #666;
}}
"""


def title_page_html(lang, page_no):
    t = TEXT[lang]
    bullets = [t["quote"], t["policy"], t["status_core"].rstrip(".") + t["status_suffix"]]
    return f"""<section class="page title" lang="{lang}">
  <h1>{esc(t['title'])}</h1>
  <p class="tagline">{render_inline_markdown(t['tagline'])}</p>
  <div class="content">
    <ul class="bullets">
      {''.join(f'<li>{render_inline_markdown(b)}</li>' for b in bullets)}
    </ul>
    <p class="cta"><a href="{DEMO_URL}">{esc(t['cta'])} → {DEMO_URL}</a></p>
  </div>
  <footer aria-hidden="true" role="presentation">
    <span>{esc(t['footer_brand'])}</span>
    <span>{page_no}/{TOTAL_PAGES}</span>
  </footer>
</section>"""


def bullet_page_html(lang, page_no, header, bullets, caveat=None):
    t = TEXT[lang]
    caveat_html = f'<p class="caveat">{render_inline_markdown(caveat)}</p>' if caveat else ""
    return f"""<section class="page" lang="{lang}">
  <h1>{esc(header)}</h1>
  <div class="content">
    <ul class="bullets">
      {''.join(f'<li>{render_inline_markdown(b)}</li>' for b in bullets)}
    </ul>
    {caveat_html}
  </div>
  <footer aria-hidden="true" role="presentation">
    <span>{esc(t['footer_brand'])}</span>
    <span>{page_no}/{TOTAL_PAGES}</span>
  </footer>
</section>"""


def links_page_html(lang, page_no, header, entries):
    t = TEXT[lang]
    items = "".join(
        f'<li>{esc(label)}: <a class="url" href="{url}">{esc(url)}</a></li>'
        for label, url in entries
    )
    return f"""<section class="page" lang="{lang}">
  <h1>{esc(header)}</h1>
  <div class="content">
    <ul class="links">{items}</ul>
  </div>
  <footer aria-hidden="true" role="presentation">
    <span>{esc(t['footer_brand'])}</span>
    <span>{page_no}/{TOTAL_PAGES}</span>
  </footer>
</section>"""


def build_document(lang, guard):
    """Returns (html, expected_pages). expected_pages is the same
    guard-approved content used to build the HTML, reused (not
    re-derived) so output validation checks exactly what was approved."""
    t = TEXT[lang]
    status = {
        "prodverified": "production-verified-scope",
        "tested": "implemented-tested",
        "notprod": "implemented-not-production-verified",
        "roadmap": "roadmap-research",
    }

    guard.assert_verbatim(lang, t["tagline"])
    guard.assert_verbatim(lang, t["quote"])
    guard.assert_verbatim(lang, t["policy"])
    guard.assert_verbatim(lang, t["status_core"])
    for b in t["how_bullets"]:
        guard.assert_verbatim(lang, b)
    for b in t["security_bullets"]:
        guard.assert_verbatim(lang, b)
    guard.assert_verbatim(lang, t["prodverified_caveat"])
    guard.assert_verbatim(lang, t["notprod_caveat"])
    guard.assert_verbatim(lang, t["roadmap_caveat"])

    # assert_section_binding ties each section's visible header to the same
    # evidence class/status as the claims rendered under it (P2.1) - not just
    # to the header's own wording in isolation.
    guard.assert_section_binding(lang, "prodverified", t["prodverified_header"], status["prodverified"])
    guard.assert_section_binding(lang, "tested", t["tested_header"], status["tested"])
    guard.assert_section_binding(lang, "notprod", t["notprod_header"], status["notprod"])
    guard.assert_section_binding(lang, "roadmap", t["roadmap1_header"], status["roadmap"])
    guard.assert_section_binding(lang, "roadmap", t["roadmap2_header"], status["roadmap"])
    guard.assert_evidence_header(lang, "prodverified", t["status_core"])  # title-page status line (no claim group)

    prodverified_bullets = [
        guard.assert_claim(lang, cid, status["prodverified"], t["prodverified"][cid])
        for cid in PRODVERIFIED_IDS
    ]
    tested_bullets = [
        guard.assert_claim(lang, cid, status["tested"], t["tested"][cid]) for cid in TESTED_IDS
    ]
    notprod_bullets = [
        guard.assert_claim(lang, cid, status["notprod"], t["notprod"][cid]) for cid in NOTPROD_IDS
    ]
    roadmap1_bullets = [
        guard.assert_claim(lang, cid, status["roadmap"], t["roadmap"][cid]) for cid in ROADMAP_IDS_1
    ]
    roadmap2_bullets = [
        guard.assert_claim(lang, cid, status["roadmap"], t["roadmap"][cid]) for cid in ROADMAP_IDS_2
    ]

    title_bullets = [t["quote"], t["policy"], t["status_core"].rstrip(".") + t["status_suffix"]]

    expected_pages = [
        {"header": t["title"], "bullets": [t["tagline"]] + title_bullets, "links": []},
        {"header": t["how_header"], "bullets": t["how_bullets"], "links": []},
        {"header": t["tested_header"], "bullets": tested_bullets, "links": []},
        {"header": t["prodverified_header"], "bullets": prodverified_bullets + [t["prodverified_caveat"]], "links": []},
        {"header": t["notprod_header"], "bullets": notprod_bullets + [t["notprod_caveat"]], "links": []},
        {"header": t["roadmap1_header"], "bullets": roadmap1_bullets, "links": []},
        {"header": t["roadmap2_header"], "bullets": roadmap2_bullets + [t["roadmap_caveat"]], "links": []},
        {"header": t["security_header"], "bullets": t["security_bullets"], "links": []},
        {"header": t["links1_header"], "bullets": [], "links": t["links1"]},
        {"header": t["links2_header"], "bullets": [], "links": t["links2"]},
    ]

    pages_html = [
        title_page_html(lang, 1),
        bullet_page_html(lang, 2, t["how_header"], t["how_bullets"]),
        bullet_page_html(lang, 3, t["tested_header"], tested_bullets),
        bullet_page_html(lang, 4, t["prodverified_header"], prodverified_bullets, t["prodverified_caveat"]),
        bullet_page_html(lang, 5, t["notprod_header"], notprod_bullets, t["notprod_caveat"]),
        bullet_page_html(lang, 6, t["roadmap1_header"], roadmap1_bullets),
        bullet_page_html(lang, 7, t["roadmap2_header"], roadmap2_bullets, t["roadmap_caveat"]),
        bullet_page_html(lang, 8, t["security_header"], t["security_bullets"]),
        links_page_html(lang, 9, t["links1_header"], t["links1"]),
        links_page_html(lang, 10, t["links2_header"], t["links2"]),
    ]
    assert len(pages_html) == TOTAL_PAGES == len(expected_pages)

    html = f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<title>{esc(t['pdf_title'])}</title>
<style>{PAGE_CSS}</style>
</head>
<body>
{''.join(pages_html)}
</body>
</html>"""
    return html, expected_pages


# --- A4 overview built directly from the approved Markdown sources ---------

A4_W_PT = 595.276
A4_H_PT = 841.89
A4_PAGE_GROUPS = [
    [0, 1],
    [2, 3],
    [4, 5],
    [6, 7],
    [8, 9],
    [10, 11],
    [12],
    [13],
]

A4_CSS = f"""
@page {{ size: {A4_W_PT}pt {A4_H_PT}pt; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  font-family: Helvetica, Arial, sans-serif;
  color: #10243d;
  -webkit-print-color-adjust: exact;
}}
section.a4-page {{
  position: relative;
  width: {A4_W_PT}pt;
  height: {A4_H_PT}pt;
  padding: 42pt 48pt 48pt;
  break-after: page;
  overflow: hidden;
}}
section.a4-page:last-child {{ break-after: auto; }}
h1 {{ font-size: 24pt; line-height: 1.15; margin: 0 0 12pt; }}
.lead p {{ font-size: 11.5pt; line-height: 1.45; margin: 0 0 14pt; }}
h2 {{ font-size: 15pt; line-height: 1.2; margin: 14pt 0 7pt; break-after: avoid; }}
p {{ font-size: 10.5pt; line-height: 1.38; margin: 0 0 7pt; }}
ul, ol {{ margin: 0 0 8pt 18pt; padding: 0; }}
li {{ font-size: 10.3pt; line-height: 1.34; margin: 0 0 4pt; }}
code {{ font-family: "Courier New", monospace; font-size: 0.92em; }}
a {{ color: #1559c7; text-decoration: underline; }}
footer {{
  position: absolute;
  left: 48pt;
  right: 48pt;
  bottom: 18pt;
  display: flex;
  justify-content: space-between;
  font-size: 8.5pt;
  color: #657387;
}}
"""


def public_document_href(url):
    if url.startswith("https://") or url.startswith("http://"):
        return url
    if url.startswith("../"):
        return f"{REPO}/blob/main/{url[3:]}"
    if url.startswith("/") or ":" in url:
        raise GenerationError(f"unsupported non-public A4 link target: {url!r}")
    return f"{REPO}/blob/main/docs/{url}"


def render_inline_markdown_with_links(raw):
    """Restricted inline renderer that preserves approved Markdown links."""
    out = []
    pos = 0
    for match in _MD_LINK_RE.finditer(raw):
        out.append(render_inline_markdown(raw[pos : match.start()]))
        label, url = match.group(1), match.group(2)
        if "[" in label or "]" in label or any(ch in url for ch in '<>"'):
            raise GenerationError(f"unsupported Markdown link in A4 source: {match.group(0)!r}")
        out.append(f'<a href="{esc(public_document_href(url))}">{render_inline_markdown(label)}</a>')
        pos = match.end()
    out.append(render_inline_markdown(raw[pos:]))
    return "".join(out)


def plain_inline_markdown(raw):
    text = _MD_LINK_RE.sub(lambda m: m.group(1), raw)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    return normalize(text)


def parse_markdown_blocks(raw):
    """Return semantic HTML plus approved visible text and links."""
    lines = raw.splitlines()
    html = []
    visible = []
    links = []
    paragraph = []
    list_kind = None
    list_items = []

    def collect_links(text):
        for match in _MD_LINK_RE.finditer(text):
            links.append((plain_inline_markdown(match.group(1)), public_document_href(match.group(2))))

    def flush_paragraph():
        if not paragraph:
            return
        text = " ".join(part.strip() for part in paragraph)
        collect_links(text)
        html.append(f"<p>{render_inline_markdown_with_links(text)}</p>")
        visible.append(plain_inline_markdown(text))
        paragraph.clear()

    def flush_list():
        nonlocal list_kind
        if not list_items:
            return
        tag = "ol" if list_kind == "ol" else "ul"
        rendered = []
        for item in list_items:
            collect_links(item)
            rendered.append(f"<li>{render_inline_markdown_with_links(item)}</li>")
            visible.append(plain_inline_markdown(item))
        html.append(f"<{tag}>{''.join(rendered)}</{tag}>")
        list_items.clear()
        list_kind = None

    for line in lines + [""]:
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_list()
            continue
        numbered = re.match(r"^\d+\.\s+(.*)$", stripped)
        bulleted = re.match(r"^-\s+(.*)$", stripped)
        if numbered or bulleted:
            flush_paragraph()
            kind = "ol" if numbered else "ul"
            if list_kind and list_kind != kind:
                flush_list()
            list_kind = kind
            list_items.append((numbered or bulleted).group(1))
            continue
        flush_list()
        paragraph.append(stripped)

    return "".join(html), visible, links


def parse_a4_source(lang):
    source = DOCS_DIR / f"kopilotti-sales-overview-{lang}.md"
    text = re.sub(r"<!--\s*sales-claim.*?-->", "", source.read_text(encoding="utf-8"))
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise GenerationError(f"A4 source is missing its H1 title: {source}")
    title = lines[0][2:].strip()
    intro_lines = []
    sections = []
    current = None
    for line in lines[1:]:
        if line.startswith("## "):
            current = {"title": line[3:].strip(), "lines": []}
            sections.append(current)
        elif current is None:
            intro_lines.append(line)
        else:
            current["lines"].append(line)
    if len(sections) != 14:
        raise GenerationError(f"expected 14 A4 source sections for {lang}, found {len(sections)}")
    return title, "\n".join(intro_lines).strip(), sections


def build_a4_document(lang):
    title, intro, sections = parse_a4_source(lang)
    total_pages = len(A4_PAGE_GROUPS)
    pages_html = []
    expected_pages = []
    for page_no, group in enumerate(A4_PAGE_GROUPS, start=1):
        chunks = []
        visible = []
        links = []
        if page_no == 1:
            intro_html, intro_visible, intro_links = parse_markdown_blocks(intro)
            chunks.append(f"<h1>{esc(title)}</h1><div class=\"lead\">{intro_html}</div>")
            visible.extend(intro_visible)
            links.extend(intro_links)
        for index in group:
            section = sections[index]
            body_html, body_visible, body_links = parse_markdown_blocks("\n".join(section["lines"]))
            chunks.append(f"<h2>{esc(section['title'])}</h2>{body_html}")
            visible.append(section["title"])
            visible.extend(body_visible)
            links.extend(body_links)
        header = title if page_no == 1 else sections[group[0]]["title"]
        expected_pages.append({"header": header, "bullets": visible, "links": links})
        pages_html.append(
            f'<section class="a4-page" lang="{lang}">{"".join(chunks)}'
            f'<footer aria-hidden="true" role="presentation"><span>Kopilotti Sales</span>'
            f'<span>{page_no}/{total_pages}</span></footer></section>'
        )

    title_meta = "Kopilotti Sales - tuote-esittely" if lang == "fi" else "Kopilotti Sales - product overview"
    html = f"""<!doctype html>
<html lang="{lang}">
<head><meta charset="utf-8"><title>{esc(title_meta)}</title><style>{A4_CSS}</style></head>
<body>{''.join(pages_html)}</body>
</html>"""
    return html, expected_pages


# --- Chrome discovery + capability probe (P1.2 / P2.2 "Chrome-portti") -----

CAPABILITY_PROBE_HTML = """<!doctype html>
<html lang="fi">
<head><meta charset="utf-8"><title>capability-probe</title>
<style>@page{size:200pt 200pt;margin:0;} body{font-family:Helvetica,Arial,sans-serif;}</style></head>
<body>
<h1>Probe</h1>
<p>probe-paragraph-marker</p>
<ul><li>probe-item-marker</li></ul>
<p><a href="https://example.invalid/probe">probe-link-marker</a></p>
</body>
</html>"""


def find_chrome():
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise GenerationError(
        "No Chromium-family browser found (checked Google Chrome.app, google-chrome, "
        "chromium, chromium-browser on PATH). This generator requires a local "
        "Chrome/Chromium with --headless --print-to-pdf tagged-PDF support; "
        "see the module docstring."
    )


def chrome_version(chrome_bin):
    out = subprocess.run([chrome_bin, "--version"], capture_output=True, text=True, timeout=30)
    return out.stdout.strip() or out.stderr.strip()


def _new_temp_pdf_path(directory, prefix, suffix):
    """A uniquely-named path inside `directory` that is guaranteed not to
    exist yet, so a later existence check proves the file was created by
    this process's Chrome invocation."""
    fd, path = tempfile.mkstemp(dir=str(directory), prefix=prefix, suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def render_html_to_pdf(chrome_bin, html_path, tmp_pdf_path, timeout=60):
    """Renders to tmp_pdf_path, which must not already exist. Returns a
    dict record of the process outcome. Raises GenerationError on any
    failure - nonzero exit, timeout, missing/symlink/empty output."""
    if os.path.exists(tmp_pdf_path) or os.path.islink(tmp_pdf_path):
        raise GenerationError(f"refusing to render: temp path already exists: {tmp_pdf_path}")

    cmd = [
        chrome_bin,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",  # required for headless Chrome inside this sandboxed CLI environment
        "--disable-extensions",
        f"--print-to-pdf={tmp_pdf_path}",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"file://{html_path}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _remove_if_exists(tmp_pdf_path)
        raise GenerationError(f"chrome timed out after {timeout}s: {exc}") from exc
    except OSError as exc:
        _remove_if_exists(tmp_pdf_path)
        raise GenerationError(f"failed to launch chrome binary {chrome_bin!r}: {exc}") from exc

    record = {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}

    if result.returncode != 0:
        _remove_if_exists(tmp_pdf_path)
        raise GenerationError(f"chrome exited {result.returncode}: {record}")
    if not os.path.exists(tmp_pdf_path):
        raise GenerationError(f"chrome exited 0 but produced no output file: {record}")
    if os.path.islink(tmp_pdf_path):
        _remove_if_exists(tmp_pdf_path)
        raise GenerationError(f"chrome output is a symlink, refusing: {tmp_pdf_path}")
    if not os.path.isfile(tmp_pdf_path):
        _remove_if_exists(tmp_pdf_path)
        raise GenerationError(f"chrome output is not a regular file: {tmp_pdf_path}")
    size = os.path.getsize(tmp_pdf_path)
    if size == 0:
        _remove_if_exists(tmp_pdf_path)
        raise GenerationError(f"chrome produced an empty file: {tmp_pdf_path}")
    return record


def _remove_if_exists(path):
    try:
        if path and os.path.exists(path) and not os.path.isdir(path):
            os.remove(path)
    except OSError:
        pass


def verify_chrome_capability(chrome_bin):
    """Runs a small known-content probe document through the real render
    path and checks the *output structure*, not just `--version`. A stub or
    a browser without tagged-PDF export support fails here, before any real
    document content is ever generated."""
    with tempfile.TemporaryDirectory() as work_dir:
        html_path = Path(work_dir) / "capability-probe.html"
        html_path.write_text(CAPABILITY_PROBE_HTML, encoding="utf-8")
        pdf_path = _new_temp_pdf_path(work_dir, "probe-", ".pdf")

        render_html_to_pdf(chrome_bin, html_path, pdf_path, timeout=30)

        try:
            pdf = pikepdf.open(pdf_path)
        except Exception as exc:
            raise GenerationError(f"capability probe: output does not parse as a PDF: {exc}") from exc

        try:
            root = pdf.Root
            mark_info = root.get("/MarkInfo")
            if mark_info is None or not bool(mark_info.get("/Marked", False)):
                raise GenerationError(
                    "capability probe: browser did not produce /MarkInfo /Marked true - "
                    "this Chrome/Chromium build does not support tagged-PDF export"
                )
            if "/StructTreeRoot" not in root:
                raise GenerationError("capability probe: browser did not produce /StructTreeRoot")
            if str(root.get("/Lang", "")) != "fi":
                raise GenerationError("capability probe: /Lang was not honored")

            counts = struct_type_counts(root["/StructTreeRoot"])
            for required_type in ("/H1", "/P", "/LI", "/Link"):
                if counts.get(required_type, 0) < 1:
                    raise GenerationError(
                        f"capability probe: missing expected structure type {required_type}; "
                        f"counts={counts}"
                    )

            text = extract_page_texts(pdf_path)[0]
            for marker in ("Probe", "probe-paragraph-marker", "probe-item-marker", "probe-link-marker"):
                if marker not in text:
                    raise GenerationError(
                        f"capability probe: expected marker {marker!r} missing from rendered "
                        f"text: {text!r}"
                    )
        finally:
            pdf.close()


# --- object-level structure validation (P1.2 / P2.2) ------------------------


def struct_type_counts(struct_tree_root):
    counts = {}
    objr_refs = []
    _walk_struct_tree(struct_tree_root.get("/K"), counts, objr_refs)
    return counts


def _walk_struct_tree(node, counts, objr_refs):
    if node is None:
        return
    if isinstance(node, pikepdf.Array):
        for item in node:
            _walk_struct_tree(item, counts, objr_refs)
        return
    if not isinstance(node, pikepdf.Dictionary):
        return  # an MCID integer leaf, not a structure element
    if node.get("/Type") == pikepdf.Name("/OBJR"):
        objr_refs.append(node.get("/Obj"))
        return
    s = node.get("/S")
    if s is not None:
        counts[str(s)] = counts.get(str(s), 0) + 1
    _walk_struct_tree(node.get("/K"), counts, objr_refs)


def collect_objr_targets(struct_tree_root):
    counts = {}
    objr_refs = []
    _walk_struct_tree(struct_tree_root.get("/K"), counts, objr_refs)
    return objr_refs


DANGEROUS_MARKERS = [
    b"/JavaScript",
    b"/Launch",
    b"/SubmitForm",
    b"/GoToR",
    b"/EmbeddedFile",
    b"/RichMedia",
]
FORBIDDEN_TEXT_MARKERS = ["`", "**", "sales-claim", "<!--", "TOTALLY BOGUS", "PLACEHOLDER", "LOREM IPSUM"]


def extract_page_texts(pdf_path):
    pages = []
    with pikepdf.open(pdf_path) as pdf:
        n = len(pdf.pages)
    for i in range(1, n + 1):
        result = subprocess.run(
            ["pdftotext", "-layout", "-f", str(i), "-l", str(i), str(pdf_path), "-"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise GenerationError(f"pdftotext failed on page {i}: {result.stderr}")
        pages.append(result.stdout)
    return pages


def validate_pdf_structure(
    pdf_path,
    lang,
    expected_pages,
    *,
    page_w=PAGE_W_PT,
    page_h=PAGE_H_PT,
    expected_h1_count=None,
    expected_h2_count=None,
    expected_link_count=10,
    allow_split_link_annotations=False,
    expect_visible_link_urls=True,
):
    total_pages = len(expected_pages)
    if expected_h1_count is None:
        expected_h1_count = total_pages
    raw = Path(pdf_path).read_bytes()
    for marker in DANGEROUS_MARKERS:
        if marker in raw:
            raise GenerationError(f"forbidden PDF action marker {marker!r} found in output")

    try:
        pdf = pikepdf.open(pdf_path)
    except Exception as exc:
        raise GenerationError(f"output does not parse as a PDF: {exc}") from exc

    try:
        if not re.match(r"^\d\.\d$", pdf.pdf_version):
            raise GenerationError(f"unexpected PDF version string: {pdf.pdf_version!r}")

        if len(pdf.pages) != total_pages:
            raise GenerationError(f"expected {total_pages} pages, got {len(pdf.pages)}")

        for i, page in enumerate(pdf.pages):
            box = [float(x) for x in page.MediaBox]
            w, h = box[2] - box[0], box[3] - box[1]
            if abs(w - page_w) > 0.5 or abs(h - page_h) > 0.5:
                raise GenerationError(f"page {i + 1} size {w}x{h}pt != {page_w}x{page_h}pt")

        root = pdf.Root
        if str(root.get("/Lang", "")) != lang:
            raise GenerationError(f"catalog /Lang = {root.get('/Lang')!r}, expected {lang!r}")

        mark_info = root.get("/MarkInfo")
        if mark_info is None or not bool(mark_info.get("/Marked", False)):
            raise GenerationError("missing or false /MarkInfo /Marked")

        struct_root = root.get("/StructTreeRoot")
        if struct_root is None:
            raise GenerationError("missing /StructTreeRoot")
        if "/ParentTree" not in struct_root:
            raise GenerationError("StructTreeRoot missing /ParentTree")

        counts = struct_type_counts(struct_root)
        if counts.get("/H1", 0) != expected_h1_count:
            raise GenerationError(
                f"expected {expected_h1_count} /H1 elements, found {counts.get('/H1', 0)}"
            )
        if expected_h2_count is not None and counts.get("/H2", 0) != expected_h2_count:
            raise GenerationError(
                f"expected {expected_h2_count} /H2 elements, found {counts.get('/H2', 0)}"
            )
        if counts.get("/LI", 0) < 1:
            raise GenerationError("no /LI list-item structure elements found")
        if counts.get("/Link", 0) != expected_link_count:
            raise GenerationError(
                f"expected {expected_link_count} /Link structure elements, found {counts.get('/Link', 0)}"
            )

        objr_targets = collect_objr_targets(struct_root)
        link_annots = []
        for page in pdf.pages:
            for annot in page.get("/Annots", []):
                if annot.get("/Subtype") == pikepdf.Name("/Link"):
                    link_annots.append(annot)
        if allow_split_link_annotations:
            if len(link_annots) < expected_link_count:
                raise GenerationError(
                    f"expected at least {expected_link_count} /Link annotations, found {len(link_annots)}"
                )
        elif len(link_annots) != expected_link_count:
            raise GenerationError(
                f"expected {expected_link_count} /Link annotations, found {len(link_annots)}"
            )
        actual_uris = []
        for annot in link_annots:
            action = annot.get("/A")
            if action is None or action.get("/S") != pikepdf.Name("/URI"):
                raise GenerationError(f"link annotation missing /A /S /URI: {annot}")
            uri = str(action.get("/URI", ""))
            if not uri.startswith(("https://", "http://")):
                raise GenerationError(f"non-public or relative URI found in PDF link annotation: {uri!r}")
            actual_uris.append(uri.rstrip("/"))
        objr_target_objgens = {(t.objgen if hasattr(t, "objgen") else None) for t in objr_targets if t is not None}
        annot_objgens = {a.objgen for a in link_annots}
        bound = annot_objgens & objr_target_objgens
        if len(bound) != len(link_annots):
            raise GenerationError(
                f"expected all {len(link_annots)} link annotations bound into the structure tree via /OBJR, "
                f"found {len(bound)}/{len(link_annots)} bound"
            )
        expected_uris = {url.rstrip("/") for page in expected_pages for _, url in page["links"]}
        missing_uris = expected_uris - set(actual_uris)
        if missing_uris:
            raise GenerationError(f"expected PDF link URI targets are missing: {sorted(missing_uris)}")

        page_texts = extract_page_texts(pdf_path)
        for i, expected in enumerate(expected_pages):
            text = page_texts[i]
            compact_text = re.sub(r"\s+", "", normalize(text))
            if re.sub(r"\s+", "", normalize(expected["header"])) not in compact_text:
                raise GenerationError(f"page {i + 1}: expected header {expected['header']!r} not found in extracted text")
            for bullet in expected["bullets"]:
                plain = re.sub(r"\s+", "", normalize(bullet))
                if plain not in compact_text:
                    raise GenerationError(
                        f"page {i + 1}: expected content {bullet!r} not found in extracted text"
                    )
            for label, url in expected["links"]:
                label_found = re.sub(r"\s+", "", normalize(label)) in compact_text
                url_found = re.sub(r"\s+", "", normalize(url)) in compact_text
                if not label_found or (expect_visible_link_urls and not url_found):
                    raise GenerationError(f"page {i + 1}: expected link {label!r}/{url!r} not found")
            for bad in FORBIDDEN_TEXT_MARKERS:
                if bad in text:
                    raise GenerationError(f"page {i + 1}: forbidden text marker {bad!r} found in extracted text: {text!r}")
    finally:
        pdf.close()


# --- deterministic metadata normalization -----------------------------------


def normalize_pdf_determinism(pdf_path, title, subject):
    pdf = pikepdf.open(pdf_path, allow_overwriting_input=True)
    di = pdf.docinfo
    di["/CreationDate"] = pikepdf.String(FIXED_DATE)
    di["/ModDate"] = pikepdf.String(FIXED_DATE)
    di["/Title"] = pikepdf.String(title)
    di["/Subject"] = pikepdf.String(subject)
    di["/Author"] = pikepdf.String("Kopilotti Sales")
    if "/Creator" in di:
        del di["/Creator"]
    di["/Creator"] = pikepdf.String(
        "kopilotti-sales-demo/scripts/generate_linkedin_overview_pdfs.py"
    )
    # deterministic_id: pikepdf otherwise mints a fresh random-looking /ID on
    # every save(), which would break byte-for-byte reproducibility even with
    # CreationDate/ModDate fixed above.
    pdf.save(pdf_path, deterministic_id=True)
    pdf.close()


# --- transactional per-language pipeline ------------------------------------


def generate_validated(lang, guard, chrome_bin, work_dir):
    """Full validated pipeline for one language. Returns the path to a
    validated temp PDF inside OUT_DIR (ready for an atomic os.replace into
    its final name), or raises GenerationError. Never touches the final
    destination path."""
    html, expected_pages = build_document(lang, guard)

    html_path = Path(work_dir) / f"kopilotti-sales-overview-{lang}-linkedin.html"
    html_path.write_text(html, encoding="utf-8")

    raw_pdf = _new_temp_pdf_path(work_dir, f"raw-{lang}-", ".pdf")
    render_html_to_pdf(chrome_bin, html_path, raw_pdf)
    validate_pdf_structure(raw_pdf, lang, expected_pages)

    # final_tmp lives inside OUT_DIR (the real docs/ directory) - not the
    # disposable work_dir - because it must be on the same filesystem as the
    # eventual destination for an atomic os.replace. That means it is NOT
    # cleaned up automatically when `with tempfile.TemporaryDirectory()`
    # exits, so if anything below fails, we must remove it ourselves before
    # propagating - otherwise a normalization or post-normalization
    # validation failure would leave a stray .tmp-*.pdf sitting in docs/
    # even though this function never returned a path for the caller to
    # track and clean up.
    final_tmp = _new_temp_pdf_path(OUT_DIR, ".tmp-", f"-{lang}-linkedin.pdf")
    try:
        shutil.copyfile(raw_pdf, final_tmp)
        normalize_pdf_determinism(final_tmp, TEXT[lang]["pdf_title"], TEXT[lang]["pdf_subject"])
        validate_pdf_structure(final_tmp, lang, expected_pages)  # re-validate post-normalization
    except Exception:
        _remove_if_exists(final_tmp)
        raise

    return final_tmp


def generate_a4_validated(lang, chrome_bin, work_dir):
    """Build and validate one A4 overview without touching its final path."""
    html, expected_pages = build_a4_document(lang)
    html_path = Path(work_dir) / f"kopilotti-sales-overview-{lang}-a4.html"
    html_path.write_text(html, encoding="utf-8")

    raw_pdf = _new_temp_pdf_path(work_dir, f"raw-{lang}-a4-", ".pdf")
    render_html_to_pdf(chrome_bin, html_path, raw_pdf)
    link_count = sum(len(page["links"]) for page in expected_pages)
    validate_pdf_structure(
        raw_pdf,
        lang,
        expected_pages,
        page_w=A4_W_PT,
        page_h=A4_H_PT,
        expected_h1_count=1,
        expected_h2_count=14,
        expected_link_count=link_count,
        allow_split_link_annotations=True,
        expect_visible_link_urls=False,
    )

    final_tmp = _new_temp_pdf_path(OUT_DIR, ".tmp-", f"-{lang}-a4.pdf")
    title = "Kopilotti Sales - tuote-esittely" if lang == "fi" else "Kopilotti Sales - product overview"
    subject = (
        "Yritysneutraali suomenkielinen tuote-esittely"
        if lang == "fi"
        else "Company-neutral English product overview"
    )
    try:
        shutil.copyfile(raw_pdf, final_tmp)
        normalize_pdf_determinism(final_tmp, title, subject)
        validate_pdf_structure(
            final_tmp,
            lang,
            expected_pages,
            page_w=A4_W_PT,
            page_h=A4_H_PT,
            expected_h1_count=1,
            expected_h2_count=14,
            expected_link_count=link_count,
            allow_split_link_annotations=True,
            expect_visible_link_urls=False,
        )
    except Exception:
        _remove_if_exists(final_tmp)
        raise
    return final_tmp


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    chrome_bin = find_chrome()
    verify_chrome_capability(chrome_bin)

    finals = {
        "fi_linkedin": Path(OUT_DIR) / "kopilotti-sales-overview-fi-linkedin.pdf",
        "en_linkedin": Path(OUT_DIR) / "kopilotti-sales-overview-en-linkedin.pdf",
        "fi_a4": Path(OUT_DIR) / "kopilotti-sales-overview-fi.pdf",
        "en_a4": Path(OUT_DIR) / "kopilotti-sales-overview-en.pdf",
    }

    tmp_to_clean = []
    try:
        with tempfile.TemporaryDirectory() as work_dir:
            generated = {}
            generated["fi_linkedin"] = generate_validated("fi", SourceGuard(), chrome_bin, work_dir)
            tmp_to_clean.append(generated["fi_linkedin"])
            generated["en_linkedin"] = generate_validated("en", SourceGuard(), chrome_bin, work_dir)
            tmp_to_clean.append(generated["en_linkedin"])
            generated["fi_a4"] = generate_a4_validated("fi", chrome_bin, work_dir)
            tmp_to_clean.append(generated["fi_a4"])
            generated["en_a4"] = generate_a4_validated("en", chrome_bin, work_dir)
            tmp_to_clean.append(generated["en_a4"])

            # Publish only after all four outputs have passed every gate.
            for key in ("fi_linkedin", "en_linkedin", "fi_a4", "en_a4"):
                os.replace(generated[key], finals[key])
                tmp_to_clean.remove(generated[key])

        print(f"chrome: {chrome_version(chrome_bin)}")
        for key, path in finals.items():
            print(f"{key} {sha256(path)}")
    finally:
        for p in tmp_to_clean:
            _remove_if_exists(p)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # fail-closed: no partial/incorrect output left claiming success
        print(f"GENERATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
