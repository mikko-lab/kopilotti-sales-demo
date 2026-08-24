"""Proof that generate_linkedin_overview_pdfs.SourceGuard actually fails closed.

Runs each failure mode listed in the module docstring against disposable,
mutated *copies* of the real docs/kopilotti-sales-overview-{fi,en}.md and
README files, in a temp directory. Never touches the real repo files.

Plain-assertion script, no test framework dependency: `python3
scripts/test_source_guard_canaries.py`.
"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_linkedin_overview_pdfs as gen  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def make_sandbox(tmp):
    """Copy the real docs/README files the guard reads into a temp sandbox."""
    docs = tmp / "docs"
    docs.mkdir()
    for name in ("kopilotti-sales-overview-fi.md", "kopilotti-sales-overview-en.md"):
        shutil.copy(ROOT / "docs" / name, docs / name)
    for name in ("README.md", "README.en.md"):
        shutil.copy(ROOT / name, tmp / name)
    return docs


def expect_raises(label, fn):
    try:
        fn()
    except (ValueError, gen.GenerationError) as exc:
        print(f"OK   {label}: raised as expected -> {exc}")
        return
    raise AssertionError(f"FAIL {label}: expected ValueError/GenerationError, nothing was raised")


def expect_ok(label, fn):
    fn()
    print(f"OK   {label}: succeeded as expected")


def canary_1_implemented_to_roadmap(tmp):
    docs = make_sandbox(tmp)
    p = docs / "kopilotti-sales-overview-fi.md"
    text = p.read_text(encoding="utf-8")
    text = text.replace(
        'id="digital-price-negotiation" status="implemented-tested"',
        'id="digital-price-negotiation" status="roadmap-research"',
    )
    p.write_text(text, encoding="utf-8")
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "1. implemented-tested -> roadmap-research",
        lambda: guard.assert_claim(
            "fi", "digital-price-negotiation", "implemented-tested", "digitaalinen hintaneuvottelu"
        ),
    )


def canary_2_roadmap_to_implemented(tmp):
    docs = make_sandbox(tmp)
    p = docs / "kopilotti-sales-overview-fi.md"
    text = p.read_text(encoding="utf-8")
    text = text.replace(
        'id="live-ddn-verification" status="roadmap-research"',
        'id="live-ddn-verification" status="implemented-tested"',
    )
    p.write_text(text, encoding="utf-8")
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "2. roadmap-research -> implemented-tested",
        lambda: guard.assert_claim(
            "fi", "live-ddn-verification", "roadmap-research", "live DDN -varmennus"
        ),
    )


def canary_3_missing_claim(tmp):
    docs = make_sandbox(tmp)
    p = docs / "kopilotti-sales-overview-fi.md"
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    out = []
    skip_next = False
    for line in lines:
        if skip_next:
            skip_next = False
            continue
        if 'id="digital-price-negotiation"' in line:
            skip_next = True  # also drop the following bullet line
            continue
        out.append(line)
    p.write_text("".join(out), encoding="utf-8")

    def attempt():
        guard = gen.SourceGuard(docs_dir=docs, root=tmp)
        guard.assert_claim(
            "fi", "digital-price-negotiation", "implemented-tested", "digitaalinen hintaneuvottelu"
        )

    # Removing the claim from FI-only also trips the FI/EN id-set check in the
    # constructor before assert_claim ever runs - either failure mode is a
    # correct "missing claim" catch, so both are accepted here.
    expect_raises("3. claim id missing from source entirely", attempt)


def canary_4_unknown_claim(tmp):
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "4. unknown claim id never defined anywhere",
        lambda: guard.assert_claim("fi", "totally-fabricated-claim-id", "implemented-tested", "x"),
    )


def canary_5_duplicate_claim(tmp):
    docs = make_sandbox(tmp)
    p = docs / "kopilotti-sales-overview-fi.md"
    text = p.read_text(encoding="utf-8")
    injected = (
        '\n<!-- sales-claim id="digital-price-negotiation" status="implemented-tested" -->\n'
        "- duplicate bullet\n"
    )
    text += injected
    p.write_text(text, encoding="utf-8")
    expect_raises(
        "5. duplicate claim id within one source file",
        lambda: gen.load_claims(p),
    )


def canary_6_fi_en_mismatch(tmp):
    docs = make_sandbox(tmp)
    p = docs / "kopilotti-sales-overview-fi.md"
    text = p.read_text(encoding="utf-8")
    text += '\n<!-- sales-claim id="fi-only-extra-claim" status="implemented-tested" -->\n- fi-vain-väite\n'
    p.write_text(text, encoding="utf-8")
    expect_raises(
        "6. FI/EN claim-id set mismatch",
        lambda: gen.SourceGuard(docs_dir=docs, root=tmp),
    )


def canary_7_visible_text_drift(tmp):
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "7. hardcoded visible text no longer matches source text for a valid id/status",
        lambda: guard.assert_claim(
            "fi",
            "digital-price-negotiation",
            "implemented-tested",
            "jotain aivan muuta tekstiä kuin lähteessä",
        ),
    )


def canary_8_baseline_still_passes(tmp):
    """Sanity check: the real generator content passes against the real (copied) sources."""
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_ok(
        "8. baseline (unmutated sandbox copy) still passes for a real claim",
        lambda: guard.assert_claim(
            "fi", "digital-price-negotiation", "implemented-tested", "digitaalinen hintaneuvottelu"
        ),
    )


def canary_9_roadmap_to_notprod(tmp):
    """The second independent review's M1 probe: the original 8 canaries only
    covered implemented<->roadmap; roadmap->not-production-verified was
    untested."""
    docs = make_sandbox(tmp)
    p = docs / "kopilotti-sales-overview-fi.md"
    text = p.read_text(encoding="utf-8")
    text = text.replace(
        'id="live-ddn-verification" status="roadmap-research"',
        'id="live-ddn-verification" status="implemented-not-production-verified"',
    )
    p.write_text(text, encoding="utf-8")
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "9. roadmap-research -> implemented-not-production-verified",
        lambda: guard.assert_claim(
            "fi", "live-ddn-verification", "roadmap-research", "live DDN -varmennus"
        ),
    )


def canary_10_zero_width_in_source(tmp):
    """The second review's M2 probe: a zero-width space injected into the
    source text must not silently make two visually-identical strings
    compare equal."""
    docs = make_sandbox(tmp)
    p = docs / "kopilotti-sales-overview-fi.md"
    text = p.read_text(encoding="utf-8")
    text = text.replace(
        "- digitaalinen hintaneuvottelu",
        "- digitaalinen​ hintaneuvottelu",
    )
    p.write_text(text, encoding="utf-8")
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "10. zero-width space injected into source claim text",
        lambda: guard.assert_claim(
            "fi", "digital-price-negotiation", "implemented-tested", "digitaalinen hintaneuvottelu"
        ),
    )


def canary_11_nfd_unicode_in_source(tmp):
    """The second review's M3b probe: NFD-decomposed a/o (combining
    diaeresis) in the source must not silently match the NFC form used in
    the generator."""
    docs = make_sandbox(tmp)
    p = docs / "kopilotti-sales-overview-fi.md"
    text = p.read_text(encoding="utf-8")
    nfd_word = "järjestelmä"  # NFD-decomposed "järjestelmä"
    text = text.replace(
        "Jälleenmyyjä määrittää säännöt. Järjestelmä soveltaa niitä johdonmukaisesti.",
        f"Jälleenmyyjä määrittää säännöt. {nfd_word.capitalize()} soveltaa niitä johdonmukaisesti.",
    )
    p.write_text(text, encoding="utf-8")
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "11. NFD-decomposed unicode in source vs NFC in generator text",
        lambda: guard.assert_verbatim(
            "fi", "Jälleenmyyjä määrittää säännöt. Järjestelmä soveltaa niitä johdonmukaisesti."
        ),
    )


SECURITY_SENTENCE_FI = (
    "LLM-eristys pienentää manipulaation vaikutusta, mutta ei ole lupaus "
    "täydellisestä prompt injection -suojasta."
)


def canary_12_hedge_truncated(tmp):
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "12. safety hedge truncated (end of sentence dropped)",
        lambda: guard.assert_verbatim(
            "fi", "LLM-eristys pienentää manipulaation vaikutusta"
        ),
    )


def canary_13_negation_dropped(tmp):
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "13. negation dropped from an approved sentence",
        lambda: guard.assert_verbatim("fi", "Tila: production-verified"),
    )


def canary_14_may_to_will(tmp):
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "14. modality changed: may -> will",
        lambda: guard.assert_verbatim(
            "en",
            "An accepted outcome will reserve the vehicle in the same database transaction "
            "as the decision, session transition, and audit event.",
        ),
    )


def canary_15_appended_contradiction(tmp):
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "15. approved sentence plus an appended contradictory follow-on sentence",
        lambda: guard.assert_verbatim(
            "en",
            "Status: not production-verified. This is fully production ready.",
        ),
    )


def canary_16_verbatim_baseline(tmp):
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_ok(
        "16. baseline: real hedge sentence still verifies exactly",
        lambda: guard.assert_verbatim("fi", SECURITY_SENTENCE_FI),
    )


def canary_17_header_overclaim_single_lang(tmp):
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "17. notprod header reclassified to a production-ready claim (single language)",
        lambda: guard.assert_evidence_header("fi", "notprod", "Tuotantovalmis ja tuotantovarmennettu"),
    )


def canary_18_roadmap_to_implemented_header(tmp):
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "18. roadmap header reclassified as implemented",
        lambda: guard.assert_evidence_header("en", "roadmap", "Currently implemented features (1/2)"),
    )


def canary_19_header_overclaim_both_langs(tmp):
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)

    def attempt():
        guard.assert_evidence_header("fi", "notprod", "Tuotantovalmis")
        guard.assert_evidence_header("en", "notprod", "Production-ready")

    expect_raises("19. header overclaim applied consistently to both languages", attempt)


def canary_20_header_wrong_evidence_class(tmp):
    """A notprod-worded header presented under the roadmap class (as if moved
    to the wrong page/section)."""
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "20. notprod-worded header checked against the roadmap evidence class",
        lambda: guard.assert_evidence_header("fi", "roadmap", "Rakennettu ja testattu, ei tuotantovarmennettu"),
    )


def canary_21_missing_status_header(tmp):
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "21. missing/empty status header",
        lambda: guard.assert_evidence_header("fi", "notprod", ""),
    )


def canary_22_header_baseline(tmp):
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)

    def attempt():
        guard.assert_evidence_header("fi", "tested", "Toteutettu ja testattu")
        guard.assert_evidence_header("en", "tested", "Implemented and tested")
        guard.assert_evidence_header("fi", "notprod", "Rakennettu ja testattu, ei tuotantovarmennettu")
        guard.assert_evidence_header("en", "notprod", "Built and tested, not production-verified")
        guard.assert_evidence_header("fi", "roadmap", "Roadmap ja tutkimussuunnat (1/2)")
        guard.assert_evidence_header("en", "roadmap", "Roadmap and research directions (1/2)")

    expect_ok("22. baseline: all six real headers verify against their evidence class", attempt)


def canary_23_inline_markdown_leak(tmp):
    """P1.1: raw backticks/asterisks must never pass through to rendered
    output unconverted or silently stripped - render_inline_markdown must
    either convert them correctly or raise."""

    def attempt():
        got = gen.render_inline_markdown("deterministinen `ACCEPT`-logiikka")
        if "`" in got:
            raise AssertionError(f"backtick leaked into rendered output: {got!r}")
        if "<code>ACCEPT</code>" not in got:
            raise AssertionError(f"code span was not converted correctly: {got!r}")

    expect_ok("23. code span converts cleanly with no leaked backticks", attempt)

    expect_raises(
        "23b. unmatched backtick raises instead of silently passing through",
        lambda: gen.render_inline_markdown("broken `markdown"),
    )


def canary_24_markdown_link_leak(tmp):
    """P1.1: a real [text](url) link must render as visible text only - no
    brackets, parens, or the raw URL leaking into the PDF (this generator
    never embeds arbitrary prose URLs; all real hyperlinks come from the
    explicit, guard-approved links pages)."""

    def attempt():
        got = gen.render_inline_markdown("check [link text](https://evil.example/x) here")
        for bad in ("[", "]", "(", ")", "https://evil.example"):
            if bad in got:
                raise AssertionError(f"markdown link syntax/URL leaked into rendered output: {got!r}")
        if "link text" not in got:
            raise AssertionError(f"link visible text was not preserved: {got!r}")

    expect_ok("24. markdown link converts to visible text only, no syntax/URL leak", attempt)


def canary_25_unknown_markdown_structure_rejected(tmp):
    """P1.1: reference-style [text][ref] links and stray unmatched brackets
    are not part of the small supported subset - they must fail closed
    rather than leak raw '[' / ']' into the rendered PDF."""
    expect_raises(
        "25a. reference-style [text][ref] link (unsupported construct) fails closed",
        lambda: gen.render_inline_markdown("see [text][ref] here"),
    )
    expect_raises(
        "25b. stray unmatched '[' fails closed",
        lambda: gen.render_inline_markdown("stray [ bracket alone"),
    )
    expect_raises(
        "25c. stray unmatched ']' fails closed",
        lambda: gen.render_inline_markdown("stray ] bracket alone"),
    )


def canary_26_raw_html_rejected(tmp):
    """P1.1: literal HTML/angle-bracket content in a source string must
    never be embedded into the template - this generator has no legitimate
    use for raw HTML in claim/framing text, so any '<'/'>' fails closed."""
    expect_raises(
        "26a. raw HTML tag in source text fails closed",
        lambda: gen.render_inline_markdown("bad <script>alert(1)</script>"),
    )
    expect_raises(
        "26b. HTML-injection-flavored payload (broken-out-of-attribute style) fails closed",
        lambda: gen.render_inline_markdown('normal text"><img src=x onerror=alert(1)>'),
    )


def canary_27_esc_escapes_html_metacharacters(tmp):
    """Defense in depth for 'HTML-escapea kaikki näkyvä teksti ennen
    templaatin muodostamista': esc() must neutralize the characters that
    matter for HTML/attribute injection, even though upstream callers
    already reject raw '<'/'>' before esc() ever sees them."""

    def attempt():
        got = gen.esc('5 < 6 & 7 > 3 "quoted"')
        expected = "5 &lt; 6 &amp; 7 &gt; 3 &quot;quoted&quot;"
        if got != expected:
            raise AssertionError(f"esc() output mismatch: got {got!r}, expected {expected!r}")

    expect_ok("27. esc() escapes <, >, &, and \" for safe template embedding", attempt)


def canary_28_header_claim_status_conflict(tmp):
    """P2.1: a header whose wording passes assert_evidence_header for one
    evidence class must still be rejected if the claims rendered under it
    were validated against a *different* status - assert_evidence_header
    alone only checks the header text in isolation."""
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "28a. 'tested'-worded header paired with roadmap-status claims",
        lambda: guard.assert_section_binding(
            "fi", "tested", "Toteutettu ja testattu", "roadmap-research"
        ),
    )
    expect_raises(
        "28b. 'notprod'-worded header paired with implemented-tested claims",
        lambda: guard.assert_section_binding(
            "en",
            "notprod",
            "Built and tested, not production-verified",
            "implemented-tested",
        ),
    )
    expect_ok(
        "28c. baseline: header/claim status binding succeeds when they agree",
        lambda: guard.assert_section_binding(
            "fi", "tested", "Toteutettu ja testattu", "implemented-tested"
        ),
    )


def canary_29_wrong_section_cross_language(tmp):
    """P2.2: a sentence that is genuinely verbatim-approved in the EN
    corpus must not validate under lang='fi' just because the words exist
    somewhere in the overall (wrong-language) corpus."""
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    expect_raises(
        "29. EN-only approved sentence asserted under lang='fi' is rejected",
        lambda: guard.assert_verbatim(
            "fi",
            "Kopilotti Sales digitizes used-vehicle price negotiation.",
        ),
    )


def canary_30_duplicated_sentence_rejected(tmp):
    """P2.2: repeating a real, individually-approved sentence twice in a
    row must not pass just because each copy matches something in the
    source - the source never contains that sentence twice back-to-back,
    so the exact in-order sequence match must fail."""
    docs = make_sandbox(tmp)
    guard = gen.SourceGuard(docs_dir=docs, root=tmp)
    doubled = f"{SECURITY_SENTENCE_FI} {SECURITY_SENTENCE_FI}"
    expect_raises(
        "30. approved sentence duplicated back-to-back is rejected",
        lambda: guard.assert_verbatim("fi", doubled),
    )


CANARIES = [
    canary_1_implemented_to_roadmap,
    canary_2_roadmap_to_implemented,
    canary_3_missing_claim,
    canary_4_unknown_claim,
    canary_5_duplicate_claim,
    canary_6_fi_en_mismatch,
    canary_7_visible_text_drift,
    canary_8_baseline_still_passes,
    canary_9_roadmap_to_notprod,
    canary_10_zero_width_in_source,
    canary_11_nfd_unicode_in_source,
    canary_12_hedge_truncated,
    canary_13_negation_dropped,
    canary_14_may_to_will,
    canary_15_appended_contradiction,
    canary_16_verbatim_baseline,
    canary_17_header_overclaim_single_lang,
    canary_18_roadmap_to_implemented_header,
    canary_19_header_overclaim_both_langs,
    canary_20_header_wrong_evidence_class,
    canary_21_missing_status_header,
    canary_22_header_baseline,
    canary_23_inline_markdown_leak,
    canary_24_markdown_link_leak,
    canary_25_unknown_markdown_structure_rejected,
    canary_26_raw_html_rejected,
    canary_27_esc_escapes_html_metacharacters,
    canary_28_header_claim_status_conflict,
    canary_29_wrong_section_cross_language,
    canary_30_duplicated_sentence_rejected,
]


def main():
    failures = 0
    for canary in CANARIES:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            try:
                canary(tmp)
            except AssertionError as exc:
                print(str(exc))
                failures += 1
    if failures:
        print(f"\n{failures} canary/canaries FAILED")
        return 1
    print(f"\nAll {len(CANARIES)} canaries behaved as expected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
