#!/usr/bin/env python
# ruff: noqa: E501
"""Build the self-contained DarwinDiff Evidence Navigator prototype."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs" / "research_map.json"
DEFAULT_OUTPUT = ROOT / "docs" / "tools" / "darwindiff_evidence_navigator.html"
DOC_PATTERN = re.compile(r"(?:^|[\s;,])(docs/[A-Za-z0-9_./+\-]+\.md)")
PROHIBITED = (
    "emulator_globe_chl1.png",
    "beats persistence at every scale tested",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _doc_paths(value: str) -> list[str]:
    return list(dict.fromkeys(DOC_PATTERN.findall(value or "")))


def _status_for_docs(value: str, documents: dict[str, dict]) -> dict[str, object]:
    paths = _doc_paths(value)
    rows = [documents[path] for path in paths if path in documents]
    tracked = bool(paths) and len(rows) == len(paths)
    local_only = any(bool(row.get("local_only")) for row in rows)
    retracted = any(bool(row.get("retracted")) for row in rows)
    return {
        "paths": paths,
        "citable": tracked and not local_only and not retracted,
        "local_only": local_only,
        "retracted_source": retracted,
    }


def _payload(source: Path) -> dict[str, object]:
    data = json.loads(source.read_text(encoding="utf-8"))
    schema = data["schema"]
    documents = {
        row["path"]: row for row in schema["document"]["rows"]
    }

    entries: list[dict[str, object]] = []
    for index, row in enumerate(schema["settled"]["rows"]):
        entries.append(
            {
                "id": f"settled-{index}",
                "relation": "settled",
                "title": row["question"],
                "body": row["answer"],
                "doc": row["doc"],
                "status": "settled",
                "parameter": "",
                **_status_for_docs(row["doc"], documents),
            }
        )

    for row in schema["claim"]["rows"]:
        if not str(row["status"]).startswith("live"):
            continue
        entries.append(
            {
                "id": row["cl_id"],
                "relation": "claim",
                "title": row["statement"],
                "body": row["detail"] or row["null_baseline"] or "",
                "doc": row["doc"],
                "status": row["status"],
                "parameter": row["parameter"] or "",
                **_status_for_docs(row["doc"], documents),
            }
        )

    for row in schema["hypothesis"]["rows"]:
        entries.append(
            {
                "id": row["hy_id"],
                "relation": "hypothesis",
                "title": row["statement"],
                "body": f"Prediction: {row['predicts']} Falsifier: {row['falsifier']}",
                "doc": row["prereg"],
                "status": row["status"],
                "parameter": "",
                **_status_for_docs(row["prereg"], documents),
            }
        )

    for index, row in enumerate(schema["trap"]["rows"]):
        entries.append(
            {
                "id": f"trap-{index}",
                "relation": "trap",
                "title": row["trap"],
                "body": "Interpretation guardrail",
                "doc": row["doc"],
                "status": "guardrail",
                "parameter": "",
                **_status_for_docs(row["doc"], documents),
            }
        )

    entries = [
        entry
        for entry in entries
        if not any(
            phrase.lower() in json.dumps(entry).lower()
            for phrase in PROHIBITED
        )
    ]

    return {
        "meta": {
            "source": source.relative_to(ROOT).as_posix(),
            "sha256": _sha256(source),
            "counts": data["counts"],
            "constraint_count": len(data["constraints"]),
            "failing_constraints": sum(
                1
                for value in data["constraints"].values()
                if not value["holds"]
            ),
            "advisory_count": len(data["advisories"]),
        },
        "parameters": schema["parameter"]["rows"],
        "entries": entries,
    }


def _render(payload: dict[str, object]) -> str:
    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    payload_json = payload_json.replace("</", "<\\/")
    meta = payload["meta"]
    counts = meta["counts"]
    template = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light" />
  <title>DarwinDiff Evidence Navigator</title>
  <style>
    :root {
      --paper: #fff;
      --ink: #090909;
      --mid: #5b5b5b;
      --rule: #a9a9a9;
      --wash: #f3f3f1;
      --serif: "Latin Modern Roman", "STIX Two Text", "Times New Roman", serif;
      --sans: "Latin Modern Sans", "Avenir Next", "Gill Sans", sans-serif;
      --mono: "Latin Modern Mono", "Courier New", monospace;
    }

    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      color: var(--ink);
      background:
        linear-gradient(to right, transparent 0 7.2vw, rgba(0,0,0,.035) 7.2vw 7.26vw, transparent 7.26vw),
        var(--paper);
      font-family: var(--serif);
    }

    a { color: inherit; text-underline-offset: .18em; }
    button, input, select { font: inherit; }
    code { font-family: var(--mono); overflow-wrap: anywhere; }

    .shell { width: min(1180px, calc(100% - 40px)); margin: 0 auto; }
    .masthead { padding: clamp(52px, 8vw, 112px) 0 34px; border-bottom: 3px solid var(--ink); }
    .eyebrow, .meta, label, .relation, .status, .source, .hash {
      font-family: var(--mono);
      letter-spacing: .065em;
      text-transform: uppercase;
    }
    .eyebrow { margin: 0 0 12px; font-size: 12px; font-weight: 700; }
    h1 { max-width: 900px; margin: 0; font-size: clamp(43px, 7vw, 88px); line-height: .93; letter-spacing: -.045em; }
    .dek { max-width: 760px; margin: 25px 0 0; font-size: clamp(18px, 2.2vw, 27px); line-height: 1.32; }
    .meta { display: flex; flex-wrap: wrap; gap: 12px 28px; margin-top: 30px; font-size: 11px; }

    .thesis { display: grid; grid-template-columns: 1.05fr .95fr; gap: 7vw; padding: 42px 0; }
    .thesis h2, .section-title { margin: 0; font-size: clamp(28px, 4vw, 52px); line-height: 1.02; letter-spacing: -.025em; }
    .thesis p { margin: 0; font-size: 18px; line-height: 1.5; }
    .thesis p + p { margin-top: 18px; }
    .boundary { padding-top: 12px; border-top: 2px solid var(--ink); }

    .patterns, .emulator, .explorer { padding: 48px 0; border-top: 1px solid var(--ink); }
    .section-intro { max-width: 780px; margin: 16px 0 30px; font-size: 18px; line-height: 1.45; }
    .pattern-list { margin: 0; }
    .pattern-row {
      display: grid;
      grid-template-columns: minmax(150px, .62fr) minmax(0, 1.38fr);
      gap: 38px;
      padding: 20px 0;
      border-top: 1px solid var(--rule);
    }
    .pattern-row:first-child { border-top: 2px solid var(--ink); }
    .pattern-row dt { font-family: var(--mono); font-size: 14px; font-weight: 700; }
    .pattern-row dt span { display: block; margin-top: 5px; color: var(--mid); font-size: 10px; font-weight: 400; text-transform: uppercase; }
    .pattern-row dd { margin: 0; font-size: 17px; line-height: 1.43; }
    .pattern-row dd small { display: block; margin-top: 7px; color: var(--mid); font-size: 13px; }

    .benchmark {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 34px;
      margin-top: 28px;
      border-top: 2px solid var(--ink);
    }
    .benchmark section { padding-top: 17px; }
    .benchmark strong { display: block; font-family: var(--mono); font-size: clamp(25px, 3.3vw, 46px); line-height: 1; }
    .benchmark span { display: block; margin-top: 9px; font-size: 15px; line-height: 1.35; }

    .controls { position: sticky; top: 0; z-index: 5; padding: 18px 0; border-top: 2px solid var(--ink); border-bottom: 1px solid var(--ink); background: rgba(255,255,255,.96); }
    .control-grid { display: grid; grid-template-columns: 2.1fr 1fr 1fr auto; gap: 14px; align-items: end; }
    label { display: block; font-size: 10px; font-weight: 700; }
    input[type="search"], select {
      width: 100%;
      margin-top: 7px;
      padding: 10px 0;
      border: 0;
      border-bottom: 1px solid var(--ink);
      border-radius: 0;
      background: transparent;
      outline: none;
    }
    input[type="search"]:focus, select:focus { border-bottom-width: 3px; }
    .check { display: flex; align-items: center; gap: 8px; min-height: 39px; white-space: nowrap; }
    .check input { accent-color: var(--ink); }

    .quick { display: flex; flex-wrap: wrap; gap: 8px 16px; margin: 18px 0 0; }
    .quick button { padding: 0; border: 0; border-bottom: 1px solid var(--ink); background: transparent; cursor: pointer; font-family: var(--mono); font-size: 11px; }
    .result-summary { margin: 25px 0 0; font-family: var(--mono); font-size: 12px; }
    .results { margin-bottom: 70px; }
    .result { display: grid; grid-template-columns: 150px minmax(0, 1fr); gap: 32px; padding: 24px 0; border-top: 1px solid var(--rule); }
    .result:first-child { border-top: 2px solid var(--ink); }
    .result-meta { font-size: 10px; line-height: 1.6; }
    .relation, .status { display: block; }
    .status { color: var(--mid); }
    .result h3 { margin: 0; font-size: clamp(19px, 2.4vw, 28px); line-height: 1.16; }
    .result p { max-width: 850px; margin: 12px 0 0; font-size: 16px; line-height: 1.47; }
    .source { display: inline-block; margin-top: 12px; font-size: 10px; text-transform: none; overflow-wrap: anywhere; }
    .source.review { font-weight: 700; text-decoration-style: double; }
    .empty { padding: 28px 0; border-top: 2px solid var(--ink); font-size: 18px; }

    footer { padding: 25px 0 55px; border-top: 3px solid var(--ink); }
    footer p { max-width: 800px; margin: 0; line-height: 1.45; }
    .hash { margin-top: 13px; color: var(--mid); font-size: 9px; overflow-wrap: anywhere; }

    @media (max-width: 760px) {
      .shell { width: min(100% - 26px, 1180px); }
      .thesis, .pattern-row, .result { grid-template-columns: 1fr; gap: 12px; }
      .benchmark { grid-template-columns: 1fr; gap: 12px; }
      .control-grid { grid-template-columns: 1fr 1fr; }
      .control-grid label:first-child { grid-column: 1 / -1; }
    }
  </style>
</head>
<body>
  <header class="masthead">
    <div class="shell">
      <p class="eyebrow">ECCO-DarwinDiff / summer research prototype</p>
      <h1>Ask what the project actually knows.</h1>
      <p class="dek">A local evidence navigator over the relational R&amp;D map: settled answers, live claims, open falsifiers, interpretation traps, and the parameter patterns that survived correction.</p>
      <div class="meta">
        <span>__SETTLED__ settled answers</span>
        <span>__CLAIMS__ claims</span>
        <span>__HYPOTHESES__ active hypotheses</span>
        <span>__CONSTRAINTS__ integrity constraints</span>
      </div>
    </div>
  </header>

  <main>
    <section class="shell thesis" aria-labelledby="thesis-title">
      <div>
        <p class="eyebrow">Summer thesis</p>
        <h2 id="thesis-title">Identifiability follows the observation, not the optimizer.</h2>
      </div>
      <div class="boundary">
        <p>Two parameters are globally recovered because real absolute anchors reach them. Two others are regionally identifiable in different basins. The two growth rates are excluded under time-mean observations.</p>
        <p>This tool is the product that is accurate enough today. The emulator is not: it is physically improved, but it does not clear a strong forecast baseline.</p>
      </div>
    </section>

    <section class="patterns">
      <div class="shell">
        <p class="eyebrow">Parameter pattern / corrected scoreboard</p>
        <h2 class="section-title">Four observable parameters, four distinct information geometries.</h2>
        <p class="section-intro">Recovery is not a single 4-of-4 score. Each parameter answers a different observational question, and the regional signals must remain regional.</p>
        <dl class="pattern-list">
          <div class="pattern-row">
            <dt>alpfe<span>global source scale</span></dt>
            <dd>Near-saturated recovery across basins; the control showing that a global source-magnitude parameter can be constrained. This is recovery under the observation suite, not validation of Carroll's numerical value.</dd>
          </div>
          <div class="pattern-row">
            <dt>R_PICPOC<span>real calcite anchor</span></dt>
            <dd>50/50 with the Daniels CP:PP anchor versus 6/50 in the epoch-matched anchor-off control. The result establishes anchor dependence, not a globally constant biological rain ratio.</dd>
          </div>
          <div class="pattern-row">
            <dt>scav_rat<span>regional / Southern Ocean</span></dt>
            <dd>Regional signal under the required geometric pooler, but still one unreplicated result and not transferable to Kerguelen. Local Fisher geometry makes vertical dissolved iron a leading symmetry-breaking candidate; conditioning did not guarantee recovery across basins.</dd>
          </div>
          <div class="pattern-row">
            <dt>diatomgraz<span>regional / EqPac</span></dt>
            <dd>Replicated out of sample at the strict 0.10 band against a 0/50 matched null. Training is anti-recovery in the other two basins, so a global aggregate would erase the actual pattern.</dd>
          </div>
          <div class="pattern-row">
            <dt>Smallgrow + Biggrow<span>excluded, not failed</span></dt>
            <dd>Time-mean observables do not separate the pair. Smallgrow has a 9/10 North Atlantic seasonal prototype that remains unconfirmed; Biggrow stays unobservable by construction.</dd>
          </div>
        </dl>
      </div>
    </section>

    <section class="emulator">
      <div class="shell">
        <p class="eyebrow">Track 2 / corrected emulator result</p>
        <h2 class="section-title">Physical validity improved. Forecast advantage did not.</h2>
        <p class="section-intro">Log-space training removed negative concentrations and restored dynamic range, but the strong baseline verdict is unchanged. That makes the emulator a research artifact, not a forecast product.</p>
        <div class="benchmark" aria-label="Corrected emulator benchmarks">
          <section><strong>-0.161</strong><span>mean skill versus per-cell seasonal AR(1), four seeds; every confidence interval remains below zero.</span></section>
          <section><strong>+0.055</strong><span>mean skill versus persistence; confidence intervals straddle zero, so the apparent gain is not significant.</span></section>
          <section><strong>1 step</strong><span>useful horizon. The engineering win is physical state quality and speed, not demonstrated predictive superiority.</span></section>
        </div>
      </div>
    </section>

    <section class="explorer" id="explorer">
      <div class="shell">
        <p class="eyebrow">Prototype / evidence decision support</p>
        <h2 class="section-title">Search the relations, not a slide author's memory.</h2>
        <p class="section-intro">The map is rebuilt from tracked sources. Results below are paragraph segments, with source status exposed rather than hidden.</p>
      </div>

      <div class="controls">
        <div class="shell">
          <div class="control-grid">
            <label>Search all terms
              <input id="query" type="search" placeholder="e.g. scav_rat vertical iron" autocomplete="off" />
            </label>
            <label>Relation
              <select id="relation">
                <option value="all">All relations</option>
                <option value="settled">Settled answers</option>
                <option value="claim">Live claims</option>
                <option value="hypothesis">Open hypotheses</option>
                <option value="trap">Interpretation traps</option>
              </select>
            </label>
            <label>Parameter
              <select id="parameter"><option value="all">All parameters</option></select>
            </label>
            <label class="check"><input id="citable" type="checkbox" checked /> tracked, non-retracted source</label>
          </div>
          <div class="quick" aria-label="Suggested searches">
            <button type="button" data-query="seasonally forced self-twin">seasonal twin</button>
            <button type="button" data-query="emulator seasonal AR1 persistence">emulator verdict</button>
            <button type="button" data-query="diatomgraz equatorial Pacific">diatomgraz EqPac</button>
            <button type="button" data-query="scav_rat vertical iron">scav_rat depth</button>
            <button type="button" data-query="R_PICPOC Daniels anchor">calcite anchor</button>
            <button type="button" data-query="continuity constrained relocation path">continuity bound</button>
          </div>
          <p class="result-summary" id="summary" aria-live="polite"></p>
        </div>
      </div>

      <div class="shell results" id="results"></div>
    </section>
  </main>

  <footer>
    <div class="shell">
      <p><strong>Boundary:</strong> this prototype helps decide what can be cited and what remains open. It does not replace the source document, verify an untrained null the corpus does not separately encode, or turn a bounded surrogate result into a Darwin-wide claim.</p>
      <p class="hash">Source __SOURCE__ / SHA-256 __SHA__ / generated without external services</p>
    </div>
  </footer>

  <script id="map-data" type="application/json">__PAYLOAD__</script>
  <script>
    (() => {
      const data = JSON.parse(document.getElementById("map-data").textContent);
      const query = document.getElementById("query");
      const relation = document.getElementById("relation");
      const parameter = document.getElementById("parameter");
      const citable = document.getElementById("citable");
      const results = document.getElementById("results");
      const summary = document.getElementById("summary");
      const limit = 60;

      const escapeHtml = (value) => String(value).replace(/[&<>"]/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;"
      })[char]);

      const sourceHref = (path) => `../../${path.replace(/\\/g, "/")}`;
      const terms = (value) => value.toLowerCase().trim().split(/\s+/).filter(Boolean);
      const textFor = (entry) => [entry.title, entry.body, entry.doc, entry.parameter, entry.id]
        .join(" ").toLowerCase();

      data.parameters.forEach((item) => {
        const option = document.createElement("option");
        option.value = item.name;
        option.textContent = item.name;
        parameter.appendChild(option);
      });

      function render() {
        const wanted = terms(query.value);
        const relationValue = relation.value;
        const parameterValue = parameter.value.toLowerCase();
        const safeOnly = citable.checked;
        const matches = data.entries.filter((entry) => {
          const haystack = textFor(entry);
          return (relationValue === "all" || entry.relation === relationValue)
            && (parameterValue === "all" || haystack.includes(parameterValue))
            && (!safeOnly || entry.citable)
            && wanted.every((term) => haystack.includes(term));
        });

        summary.textContent = `${matches.length} matching relation${matches.length === 1 ? "" : "s"}`
          + (matches.length > limit ? ` / showing first ${limit}` : "");

        if (!matches.length) {
          results.innerHTML = '<p class="empty">No matching relation. Remove a term or include sources marked for review.</p>';
          return;
        }

        results.innerHTML = matches.slice(0, limit).map((entry) => {
          const path = entry.paths[0] || "";
          const sourceClass = entry.citable ? "source" : "source review";
          const sourceLabel = entry.citable ? entry.doc : `${entry.doc} / review source status`;
          const source = path
            ? `<a class="${sourceClass}" href="${sourceHref(path)}">${escapeHtml(sourceLabel)}</a>`
            : `<span class="${sourceClass}">${escapeHtml(sourceLabel || "No tracked document path")}</span>`;
          return `<article class="result">
            <div class="result-meta">
              <span class="relation">${escapeHtml(entry.relation)}</span>
              <span class="status">${escapeHtml(entry.status)}</span>
              <code>${escapeHtml(entry.id)}</code>
            </div>
            <div>
              <h3>${escapeHtml(entry.title)}</h3>
              <p>${escapeHtml(entry.body)}</p>
              ${source}
            </div>
          </article>`;
        }).join("");
      }

      [query, relation, parameter, citable].forEach((control) => {
        control.addEventListener(control === query ? "input" : "change", render);
      });
      document.querySelectorAll("[data-query]").forEach((button) => {
        button.addEventListener("click", () => {
          query.value = button.dataset.query;
          relation.value = "all";
          parameter.value = "all";
          render();
          document.getElementById("explorer").scrollIntoView({ behavior: "smooth" });
        });
      });

      query.value = "parameter identifiability";
      render();
    })();
  </script>
</body>
</html>
'''
    replacements = {
        "__SETTLED__": str(counts["settled"]),
        "__CLAIMS__": str(counts["claim"]),
        "__HYPOTHESES__": str(counts["hypothesis"]),
        "__CONSTRAINTS__": str(meta["constraint_count"]),
        "__SOURCE__": str(meta["source"]),
        "__SHA__": str(meta["sha256"]),
        "__PAYLOAD__": payload_json,
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    return template


def build(source: Path, output: Path) -> str:
    payload = _payload(source)
    if payload["meta"]["failing_constraints"]:
        raise RuntimeError("research-map export reports failing integrity constraints")
    html = _render(payload)
    for phrase in PROHIBITED:
        if phrase.lower() in html.lower():
            raise RuntimeError(f"prohibited presentation content found: {phrase}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8", newline="\n")
    return html


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    html = build(args.source.resolve(), args.output.resolve())
    print(f"wrote {args.output}  {len(html):,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
