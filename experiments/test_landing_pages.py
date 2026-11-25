#!/usr/bin/env python3
"""The three landing pages are documents too, so hold them to the same rules.

`en/`, `ko/` and `zh/index.html` are what a visitor reads first, and until now
nothing checked them: they could quote a retired number, drift from the paper, or
show a figure that no longer exists. The markdown guards never saw them because
they are HTML.

Three rules, the same ones the paper obeys:

1. **Same numbers, three languages.** A reader who switches language must not get a
   different claim. Comparing multisets rather than order, because word order moves.
2. **Each page links its own paper.** A language page that points at another
   language's draft is how a translation silently becomes the source.
3. **No retired value.** The registry in `RETIRED_NUMBERS.md` applies here too; these
   pages were written in the legacy era and are exactly where old numbers survive.

Run: python3 experiments/test_landing_pages.py
"""

import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_retired_numbers as registry_module  # noqa: E402

PAGES = {"en": "en/index.html", "ko": "ko/index.html", "zh": "zh/index.html"}
PAPERS = {"en": "PAPER_DRAFT.html", "ko": "PAPER_DRAFT_KO.html", "zh": "PAPER_DRAFT_CN.html"}
FIGURES = ("fig4_where_the_results_sit.png", "fig1_gap_vs_graph_size.png",
           "fig2_queue_ceiling.png", "fig3_localisation_auc.png")


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
        return handle.read()


def body(page):
    """The prose only: CSS colours and pixel widths are not claims."""
    html = read(page)
    start, end = html.index("<main>"), html.index("</main>")
    text = re.sub(r"<[^>]+>", " ", html[start:end])
    return text.replace("\u2212", "-")


def numbers(page):
    tokens = re.findall(r"\d[\d,]*(?:\.\d+)?%?", body(page))
    return collections.Counter(token.strip(".,;:") for token in tokens)


def test_the_three_pages_carry_the_same_numbers():
    """A language switch may change the words, never a value."""
    counts = {lang: numbers(page) for lang, page in PAGES.items()}
    assert all(counts.values()), "a landing page states no numbers at all"
    base = counts["en"]
    for lang, seen in counts.items():
        if seen == base:
            continue
        extra = {k: seen[k] - base[k] for k in seen if seen[k] > base[k]}
        missing = {k: base[k] - seen[k] for k in base if base[k] > seen[k]}
        raise AssertionError(f"{lang} disagrees with en: extra {extra}, missing {missing}")


def test_each_page_links_its_own_paper():
    """The English page links the English draft; so do the others, in their language."""
    for lang, page in PAGES.items():
        html = read(page)
        own = PAPERS[lang]
        assert own in html, f"{page} does not link {own}"
        for other in PAPERS.values():
            assert other in html, f"{page} hides {other}; readers switch languages"


def test_no_page_quotes_a_retired_number():
    """The registry was written for markdown; these pages are where old values hid."""
    rows = registry_module.registry()
    offenders = []
    for page in PAGES.values():
        text = body(page)
        for pattern, replacement, commit, _, _ in rows:
            for match in pattern.finditer(text):
                line = text[max(0, match.start() - 60):match.end() + 60]
                offenders.append(f"{page}: still cites /{pattern.pattern}/ "
                                 f"(retired by {commit}, now {replacement}): "
                                 f"{' '.join(line.split())[:90]}")
    assert not offenders, "\n".join(offenders)


def test_the_pages_link_figures_that_exist():
    """A landing page whose picture 404s is the first thing a reader sees."""
    for page in PAGES.values():
        html = read(page)
        for name in FIGURES:
            assert name in html, f"{page} never shows {name}"
            assert os.path.isfile(os.path.join(ROOT, "figures", name)), name


def main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok  ", fn.__name__)
    print(f"{len(fns)}/{len(fns)} passed")


if __name__ == "__main__":
    main()
