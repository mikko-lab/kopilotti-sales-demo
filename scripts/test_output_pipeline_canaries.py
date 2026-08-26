"""Chrome-output-trust-boundary fail-closed canaries for
generate_linkedin_overview_pdfs.py (P1.2 / P2.2 "Chrome-portti").

The second independent re-review's core complaint was that the previous
generator trusted Chrome's exit code alone as proof that a new, correct PDF
had been produced. This file proves every failure mode from that review's
mandatory canary list is actually rejected by the current transactional
pipeline (render_html_to_pdf / validate_pdf_structure / verify_chrome_capability
/ generate_validated / main), *including* the specific "fabricated Chromium 90"
stub the re-review used to defeat a naive `--version`-only check.

Two kinds of fixtures are used:

- Structural mutation canaries (A-series): start from the real, already
  validated docs/kopilotti-sales-overview-{fi,en}-linkedin.pdf on disk (or a
  fresh minimal PDF), mutate a disposable *copy* with pikepdf, and run
  validate_pdf_structure directly against it. The real repo files are only
  ever read, never opened for writing.

- Process/pipeline canaries (B-series): small fake "chrome" executables
  (this same interpreter, so pikepdf is importable) stand in for
  chrome_bin, simulating exit codes/output the real Chrome could never be
  coaxed into producing. generate_validated/main are always pointed at a
  disposable sandbox OUT_DIR (via monkeypatching gen.OUT_DIR), never at the
  real docs/ directory.

Plain-assertion script, no test framework dependency:
`python3 scripts/test_output_pipeline_canaries.py`.
"""

import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_linkedin_overview_pdfs as gen  # noqa: E402
import pikepdf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REAL_FI_PDF = ROOT / "docs" / "kopilotti-sales-overview-fi-linkedin.pdf"
REAL_EN_PDF = ROOT / "docs" / "kopilotti-sales-overview-en-linkedin.pdf"
REAL_FI_A4_PDF = ROOT / "docs" / "kopilotti-sales-overview-fi.pdf"
REAL_EN_A4_PDF = ROOT / "docs" / "kopilotti-sales-overview-en.pdf"
REAL_CHROME = gen.find_chrome()


def expect_raises(label, fn):
    try:
        fn()
    except (ValueError, gen.GenerationError) as exc:
        print(f"OK   {label}: raised as expected -> {exc}")
        return
    raise AssertionError(f"FAIL {label}: expected GenerationError/ValueError, nothing was raised")


def expect_ok(label, fn):
    fn()
    print(f"OK   {label}: succeeded as expected")


def real_expected_pages(lang):
    return gen.build_document(lang, gen.SourceGuard())[1]


def real_link_count(lang):
    """The 8-page LinkedIn carousel deliberately carries far fewer links (2:
    demo + public repo, both on the closing page) than the old 10-page deck
    did - validate_pdf_structure's expected_link_count default (10) is
    stale for these real fi/en outputs, so canaries that validate against
    them must pass the real, current count explicitly (same pattern
    generate_validated/generate_a4_validated already use)."""
    return sum(len(p["links"]) for p in real_expected_pages(lang))


def write_fake_chrome(dir_path, name, body):
    """Writes an executable fake-chrome script (this interpreter, so
    pikepdf is importable) that mimics `chrome_bin --version` /
    `chrome_bin ... --print-to-pdf=X ... file://Y` well enough to stand in
    for chrome_bin in render_html_to_pdf/verify_chrome_capability."""
    path = Path(dir_path) / name
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return str(path)


def parse_args_body(version_string="HeadlessChrome/999.0.0.0 fake-stub"):
    return f"""
import os
import sys
args = sys.argv[1:]
pdf_path = None
html_arg = None
for a in args:
    if a.startswith("--print-to-pdf="):
        pdf_path = a[len("--print-to-pdf="):]
    if a.startswith("file://"):
        html_arg = a
if "--version" in args:
    print({version_string!r})
    sys.exit(0)
"""


PARSE_ARGS = parse_args_body()


class Monkeypatch:
    """Minimal save/restore for module attributes, scoped to one canary."""

    def __init__(self):
        self._saved = []

    def set(self, obj, name, value):
        self._saved.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def undo(self):
        for obj, name, value in reversed(self._saved):
            setattr(obj, name, value)
        self._saved.clear()


# --- A-series: validate_pdf_structure structural-mutation canaries ---------


def canary_a1_one_page(tmp):
    with pikepdf.open(REAL_FI_PDF) as pdf:
        del pdf.pages[1:]
        out = tmp / "one-page.pdf"
        pdf.save(out)
    expect_raises(
        "A1. exit 0 + 1-page PDF",
        lambda: gen.validate_pdf_structure(out, "fi", real_expected_pages("fi")),
    )


def canary_a2_wrong_page_size(tmp):
    with pikepdf.open(REAL_FI_PDF) as pdf:
        for page in pdf.pages:
            page.MediaBox = [0, 0, 200, 200]
        out = tmp / "wrong-size.pdf"
        pdf.save(out)
    expect_raises(
        "A2. exit 0 + 200x200pt PDF",
        lambda: gen.validate_pdf_structure(out, "fi", real_expected_pages("fi")),
    )


def canary_a3_untagged(tmp):
    with pikepdf.open(REAL_FI_PDF) as pdf:
        if "/MarkInfo" in pdf.Root:
            del pdf.Root["/MarkInfo"]
        out = tmp / "untagged.pdf"
        pdf.save(out)
    expect_raises(
        "A3. exit 0 + untagged PDF (missing /MarkInfo)",
        lambda: gen.validate_pdf_structure(out, "fi", real_expected_pages("fi")),
    )


def canary_a4_wrong_lang(tmp):
    with pikepdf.open(REAL_FI_PDF) as pdf:
        pdf.Root["/Lang"] = pikepdf.String("xx")
        out = tmp / "wrong-lang.pdf"
        pdf.save(out)
    expect_raises(
        "A4. exit 0 + wrong /Lang",
        lambda: gen.validate_pdf_structure(out, "fi", real_expected_pages("fi")),
    )


def canary_a5_placeholder_text(tmp):
    guard = gen.SourceGuard()
    html, expected_pages = gen.build_document("fi", guard)
    t = gen.TEXT["fi"]
    marker_html = html.replace(
        f"<h1>{gen.esc(t['title'])}</h1>",
        f"<h1>{gen.esc(t['title'])}</h1><p>PLACEHOLDER</p>",
        1,
    )
    assert marker_html != html, "test setup: title <h1> not found to inject PLACEHOLDER near"
    html_path = tmp / "placeholder.html"
    html_path.write_text(marker_html, encoding="utf-8")
    pdf_path = gen._new_temp_pdf_path(tmp, "placeholder-", ".pdf")
    gen.render_html_to_pdf(REAL_CHROME, html_path, pdf_path)
    expect_raises(
        "A5. exit 0 + leftover placeholder text in rendered output",
        lambda: gen.validate_pdf_structure(
            pdf_path, "fi", expected_pages, expected_link_count=real_link_count("fi")
        ),
    )


def canary_a6_missing_claim(tmp):
    expected_pages = real_expected_pages("fi")
    link_count = real_link_count("fi")
    tampered = [dict(p, bullets=list(p["bullets"])) for p in expected_pages]
    tampered[2]["bullets"].append("täysin keksitty väite joka ei ole PDF:ssä")
    expect_raises(
        "A6. exit 0 + expected claim missing from rendered output",
        lambda: gen.validate_pdf_structure(REAL_FI_PDF, "fi", tampered, expected_link_count=link_count),
    )


def canary_a7_missing_link(tmp):
    expected_pages = real_expected_pages("fi")
    # Intentionally the *pre-tamper* link count: only the extra link's URI
    # is missing from the rendered output, not an extra link annotation, so
    # the struct/annotation count must still match the real, untampered
    # count for this canary to exercise the URI-presence check rather than
    # failing earlier at the count check for the wrong reason.
    link_count = real_link_count("fi")
    tampered = [dict(p, links=list(p["links"])) for p in expected_pages]
    tampered[7]["links"].append(("Keksitty linkki", "https://example.invalid/keksitty"))
    expect_raises(
        "A7. exit 0 + expected link missing from rendered output",
        lambda: gen.validate_pdf_structure(REAL_FI_PDF, "fi", tampered, expected_link_count=link_count),
    )


def canary_a8_corrupted_pdf(tmp):
    out = tmp / "corrupted.pdf"
    out.write_bytes(b"%PDF-1.4\nthis is not actually a valid pdf body\n")
    expect_raises(
        "A8. corrupted/unparseable PDF",
        lambda: gen.validate_pdf_structure(out, "fi", real_expected_pages("fi")),
    )


def canary_a9_baseline_still_passes(tmp):
    """Sanity check: the real, unmutated fi/en PDFs on disk still validate
    against their own real expected_pages."""
    expect_ok(
        "A9. baseline: real fi/en outputs still validate cleanly",
        lambda: (
            gen.validate_pdf_structure(
                REAL_FI_PDF, "fi", real_expected_pages("fi"), expected_link_count=real_link_count("fi")
            ),
            gen.validate_pdf_structure(
                REAL_EN_PDF, "en", real_expected_pages("en"), expected_link_count=real_link_count("en")
            ),
        ),
    )


def canary_a10_a4_baseline_still_passes(tmp):
    def validate(lang, path):
        _, expected_pages = gen.build_a4_document(lang)
        link_count = sum(len(page["links"]) for page in expected_pages)
        gen.validate_pdf_structure(
            path,
            lang,
            expected_pages,
            page_w=gen.A4_W_PT,
            page_h=gen.A4_H_PT,
            expected_h1_count=1,
            expected_h2_count=14,
            expected_link_count=link_count,
            allow_split_link_annotations=True,
            expect_visible_link_urls=False,
        )

    expect_ok(
        "A10. baseline: real FI/EN A4 outputs still validate cleanly",
        lambda: (validate("fi", REAL_FI_A4_PDF), validate("en", REAL_EN_A4_PDF)),
    )


# --- B-series: process/pipeline fail-closed canaries -----------------------


def canary_b1_exit0_no_output_file(tmp):
    fake = write_fake_chrome(
        tmp,
        "fake-chrome-no-output",
        PARSE_ARGS + "\nsys.exit(0)\n",
    )
    html_path = tmp / "x.html"
    html_path.write_text("<html><body>x</body></html>", encoding="utf-8")
    target = gen._new_temp_pdf_path(tmp, "t-", ".pdf")
    expect_raises(
        "B1. exit 0 but no new output file produced",
        lambda: gen.render_html_to_pdf(fake, html_path, target),
    )
    assert not os.path.exists(target), "B1: no stray file should be left behind"


def canary_b2_exit_nonzero_partial_file(tmp):
    fake = write_fake_chrome(
        tmp,
        "fake-chrome-partial-nonzero",
        PARSE_ARGS
        + "\nopen(pdf_path, 'wb').write(b'%PDF-1.4 partial garbage')\nsys.exit(1)\n",
    )
    html_path = tmp / "x.html"
    html_path.write_text("<html><body>x</body></html>", encoding="utf-8")
    target = gen._new_temp_pdf_path(tmp, "t-", ".pdf")

    def attempt():
        gen.render_html_to_pdf(fake, html_path, target)

    expect_raises("B2. nonzero exit + partial output file written", attempt)
    assert not os.path.exists(target), "B2: partial output must be removed on nonzero exit"


def canary_b3_process_dies_mid_render(tmp):
    fake = write_fake_chrome(
        tmp,
        "fake-chrome-dies",
        PARSE_ARGS
        + (
            "\nimport signal\n"
            "f = open(pdf_path, 'wb')\n"
            "f.write(b'%PDF-1.4 half-written')\n"
            "f.flush()\n"
            "f.close()\n"
            "os.kill(os.getpid(), signal.SIGKILL)\n"
        ),
    )
    html_path = tmp / "x.html"
    html_path.write_text("<html><body>x</body></html>", encoding="utf-8")
    target = gen._new_temp_pdf_path(tmp, "t-", ".pdf")

    def attempt():
        gen.render_html_to_pdf(fake, html_path, target)

    expect_raises("B3. chrome process killed mid-render (nonzero/negative exit)", attempt)
    assert not os.path.exists(target), "B3: partial output from a killed process must be removed"


def canary_b4_old_destination_survives_no_new_file(tmp):
    mp = Monkeypatch()
    sandbox_out = tmp / "out"
    sandbox_out.mkdir()
    fi_final = sandbox_out / "kopilotti-sales-overview-fi-linkedin.pdf"
    fi_final.write_bytes(b"PRE-EXISTING FINAL PDF BYTES - MUST NOT CHANGE")
    original_bytes = fi_final.read_bytes()
    try:
        mp.set(gen, "OUT_DIR", sandbox_out)
        fake = write_fake_chrome(tmp, "fake-chrome-no-output-b4", PARSE_ARGS + "\nsys.exit(0)\n")
        guard = gen.SourceGuard()

        def attempt():
            with tempfile.TemporaryDirectory() as work_dir:
                gen.generate_validated("fi", guard, fake, work_dir)

        expect_raises(
            "B4. old final destination exists but chrome produces no new file",
            attempt,
        )
        assert fi_final.read_bytes() == original_bytes, "B4: pre-existing final must be untouched"
        leftovers = list(sandbox_out.glob("*"))
        assert leftovers == [fi_final], f"B4: no stray temp files may remain in OUT_DIR, found {leftovers}"
    finally:
        mp.undo()


def canary_b5_fi_succeeds_en_fails_no_partial_publish(tmp):
    mp = Monkeypatch()
    sandbox_out = tmp / "out"
    sandbox_out.mkdir()
    fi_final = sandbox_out / "kopilotti-sales-overview-fi-linkedin.pdf"
    en_final = sandbox_out / "kopilotti-sales-overview-en-linkedin.pdf"
    fi_final.write_bytes(b"PRE-EXISTING FI FINAL - MUST NOT CHANGE")
    en_final.write_bytes(b"PRE-EXISTING EN FINAL - MUST NOT CHANGE")
    fi_before, en_before = fi_final.read_bytes(), en_final.read_bytes()

    body = (
        PARSE_ARGS
        + f"\nREAL_CHROME = {REAL_CHROME!r}\n"
        + (
            "if html_arg and '-en-' in html_arg:\n"
            "    sys.exit(1)\n"
            "else:\n"
            "    import subprocess\n"
            "    r = subprocess.run([REAL_CHROME] + args)\n"
            "    sys.exit(r.returncode)\n"
        )
    )
    try:
        mp.set(gen, "OUT_DIR", sandbox_out)
        fake = write_fake_chrome(tmp, "fake-chrome-fi-ok-en-fail", body)
        mp.set(gen, "find_chrome", lambda: fake)

        expect_raises("B5. FI generation succeeds, EN generation fails -> neither final is published", gen.main)

        assert fi_final.read_bytes() == fi_before, "B5: fi final must remain untouched when en fails"
        assert en_final.read_bytes() == en_before, "B5: en final must remain untouched when en fails"
        leftovers = [p for p in sandbox_out.glob("*") if p not in (fi_final, en_final)]
        assert not leftovers, f"B5: no stray temp files may remain in OUT_DIR, found {leftovers}"
    finally:
        mp.undo()


def canary_b6_normalization_fails(tmp):
    mp = Monkeypatch()
    sandbox_out = tmp / "out"
    sandbox_out.mkdir()
    try:
        mp.set(gen, "OUT_DIR", sandbox_out)

        def failing_normalize(pdf_path, title, subject):
            raise gen.GenerationError("simulated normalization failure")

        mp.set(gen, "normalize_pdf_determinism", failing_normalize)
        guard = gen.SourceGuard()

        def attempt():
            with tempfile.TemporaryDirectory() as work_dir:
                gen.generate_validated("fi", guard, REAL_CHROME, work_dir)

        expect_raises("B6. normalization step fails after raw validation passed", attempt)
        leftovers = list(sandbox_out.glob("*"))
        assert not leftovers, f"B6: no stray temp files may remain in OUT_DIR, found {leftovers}"
    finally:
        mp.undo()


def canary_b7_post_normalization_validation_fails(tmp):
    mp = Monkeypatch()
    sandbox_out = tmp / "out"
    sandbox_out.mkdir()
    real_normalize = gen.normalize_pdf_determinism
    try:
        mp.set(gen, "OUT_DIR", sandbox_out)

        def corrupting_normalize(pdf_path, title, subject):
            real_normalize(pdf_path, title, subject)
            with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
                if "/MarkInfo" in pdf.Root:
                    del pdf.Root["/MarkInfo"]
                pdf.save(pdf_path)

        mp.set(gen, "normalize_pdf_determinism", corrupting_normalize)
        guard = gen.SourceGuard()

        def attempt():
            with tempfile.TemporaryDirectory() as work_dir:
                gen.generate_validated("fi", guard, REAL_CHROME, work_dir)

        expect_raises(
            "B7. post-normalization re-validation catches normalization-introduced corruption",
            attempt,
        )
        leftovers = list(sandbox_out.glob("*"))
        assert not leftovers, f"B7: no stray temp files may remain in OUT_DIR, found {leftovers}"
    finally:
        mp.undo()


def canary_b8_fabricated_chromium_90_stub_rejected(tmp):
    """The second independent re-review's own fabricated "Chromium 90" stub:
    answers --version with a plausible-looking version string, but its
    --print-to-pdf output is an ordinary, untagged, wrong-size, 1-page PDF.
    A version-string-only check would accept this; verify_chrome_capability
    must not."""
    body = (
        parse_args_body("Chromium 90.0.4430.212")
        + (
            "\nimport pikepdf\n"
            "pdf = pikepdf.new()\n"
            "pdf.add_blank_page(page_size=(200, 200))\n"
            "pdf.save(pdf_path)\n"
            "sys.exit(0)\n"
        )
    )
    fake = write_fake_chrome(tmp, "fake-chromium-90-stub", body)
    import subprocess

    version_out = subprocess.run([fake, "--version"], capture_output=True, text=True, timeout=10)
    assert "90" in version_out.stdout, "test setup: stub must claim to be Chromium 90"
    expect_raises(
        "B8. fabricated 'Chromium 90' stub (plausible --version, untagged/wrong-size output) rejected",
        lambda: gen.verify_chrome_capability(fake),
    )


def canary_b9_only_linkedin_leaves_a4_untouched(tmp):
    """--only=linkedin (added for the LinkedIn Carousel Current State slice)
    must generate only the two LinkedIn PDFs and never open, re-render, or
    overwrite the two A4 PDFs - a real end-to-end gen.main() run, same
    pattern as B5, so this exercises the actual CLI flag parsing in main()
    rather than just the keys-selection dict in isolation."""
    mp = Monkeypatch()
    sandbox_out = tmp / "out"
    sandbox_out.mkdir()
    fi_a4 = sandbox_out / "kopilotti-sales-overview-fi.pdf"
    en_a4 = sandbox_out / "kopilotti-sales-overview-en.pdf"
    fi_linkedin = sandbox_out / "kopilotti-sales-overview-fi-linkedin.pdf"
    en_linkedin = sandbox_out / "kopilotti-sales-overview-en-linkedin.pdf"
    fi_a4.write_bytes(b"PRE-EXISTING A4 FI - MUST NOT CHANGE")
    en_a4.write_bytes(b"PRE-EXISTING A4 EN - MUST NOT CHANGE")
    fi_a4_before, en_a4_before = fi_a4.read_bytes(), en_a4.read_bytes()
    fi_a4_mtime_before, en_a4_mtime_before = fi_a4.stat().st_mtime_ns, en_a4.stat().st_mtime_ns

    try:
        mp.set(gen, "OUT_DIR", sandbox_out)
        mp.set(sys, "argv", ["generate_linkedin_overview_pdfs.py", "--only=linkedin"])

        expect_ok("B9. --only=linkedin succeeds and generates only the LinkedIn pair", gen.main)

        assert fi_linkedin.exists(), "B9: fi-linkedin.pdf must be generated"
        assert en_linkedin.exists(), "B9: en-linkedin.pdf must be generated"
        assert fi_a4.read_bytes() == fi_a4_before, "B9: A4 fi must stay byte-identical, --only=linkedin must never touch it"
        assert en_a4.read_bytes() == en_a4_before, "B9: A4 en must stay byte-identical, --only=linkedin must never touch it"
        assert fi_a4.stat().st_mtime_ns == fi_a4_mtime_before, "B9: A4 fi mtime must be untouched (never opened for writing)"
        assert en_a4.stat().st_mtime_ns == en_a4_mtime_before, "B9: A4 en mtime must be untouched (never opened for writing)"
        leftovers = [p for p in sandbox_out.glob("*") if p not in (fi_a4, en_a4, fi_linkedin, en_linkedin)]
        assert not leftovers, f"B9: no stray temp files may remain in OUT_DIR, found {leftovers}"
    finally:
        mp.undo()


def canary_c1_contrast_margins(tmp):
    """Every secondary/small text-on-background pair used on the carousel
    (footer, p.caveat, span.url-sub) must clear WCAG AA with real margin,
    not a bare pass. Two prior rounds shipped colors that passed AA with
    ~0 headroom (4.50:1 footer, 4.505:1 caveat, 4.83:1 url-sub) - this
    reads gen.CONTRAST_PAIRS/gen.CONTRAST_MIN_RATIO directly (the same
    table the generator's own palette comment points at) so the check and
    the palette can never silently drift apart."""
    del tmp
    assert gen.CONTRAST_MIN_RATIO > 4.5, "C1: minimum ratio must itself have margin above the bare WCAG AA floor"
    for label, fg, bg in gen.CONTRAST_PAIRS:
        ratio = gen.contrast_ratio(fg, bg)
        assert ratio >= gen.CONTRAST_MIN_RATIO, (
            f"C1: {label} ({fg} on {bg}) = {ratio:.2f}:1, below required {gen.CONTRAST_MIN_RATIO}:1"
        )
    print(
        f"OK   C1. all {len(gen.CONTRAST_PAIRS)} contrast pairs clear "
        f"{gen.CONTRAST_MIN_RATIO}:1 with margin above the 4.5:1 WCAG AA floor"
    )


CANARIES = [
    canary_a1_one_page,
    canary_a2_wrong_page_size,
    canary_a3_untagged,
    canary_a4_wrong_lang,
    canary_a5_placeholder_text,
    canary_a6_missing_claim,
    canary_a7_missing_link,
    canary_a8_corrupted_pdf,
    canary_a9_baseline_still_passes,
    canary_a10_a4_baseline_still_passes,
    canary_b1_exit0_no_output_file,
    canary_b2_exit_nonzero_partial_file,
    canary_b3_process_dies_mid_render,
    canary_b4_old_destination_survives_no_new_file,
    canary_b5_fi_succeeds_en_fails_no_partial_publish,
    canary_b6_normalization_fails,
    canary_b7_post_normalization_validation_fails,
    canary_b8_fabricated_chromium_90_stub_rejected,
    canary_b9_only_linkedin_leaves_a4_untouched,
    canary_c1_contrast_margins,
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
