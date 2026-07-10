# TikZ figures — DarwinDiff

Publication-quality, scientifically-faithful TikZ source for the project's core diagrams.
Each figure is a self-contained [`standalone`](https://ctan.org/pkg/standalone) document that
loads the shared style `darwindiff-tikz.sty`, so it compiles on its own **and** can be `\input`
into the paper.

## Figures

| file | shows |
|---|---|
| [`pipeline.tex`](pipeline.tex) | the differentiable parameter-learner pipeline vs Green's-functions calibration — the method |
| [`param_identifiability.tex`](param_identifiability.tex) | the six Carroll-6 parameters, the real observable that could constrain each, the verdict, and the verified recovery (Paper #1) |
| [`closure_map.tex`](closure_map.tex) | the Track-2 identifiability-limits map — the three closures and the distinct reason real observations can't constrain each (Paper #2) |

## Compile a figure on its own

```bash
pdflatex pipeline.tex                                     # -> pipeline.pdf
pdftocairo -png -r 150 -singlefile pipeline.pdf pipeline  # optional PNG preview
```

## Embed in the paper

Load the `standalone` package once, then `\input` each figure inside a `figure` environment:

```latex
\usepackage{standalone}
% ...
\begin{figure}
  \centering
  \input{docs/figures/tikz/pipeline}
  \caption{The DarwinDiff differentiable parameter-learner pipeline.}
\end{figure}
```

Put `darwindiff-tikz.sty` on the paper's `TEXINPUTS` (or copy it beside `main.tex`). Colours
are colourblind-safe and legible in greyscale — verdict is encoded by a light fill tint **and**
a text label, not hue alone.

## Scientific accuracy

Every number is transcribed from the verified-experiment-loop record ([STATUS.md](../../../STATUS.md),
the Track-2 write-up, and the reproducibility appendix): iron pair **38/40**; the per-cell trio
{`alpfe`, `scav_rat`, `R_PICPOC`} **7/10** vs **0/10** for a global-scalar vector; `R_PICPOC`
**50/50** vs the Daniels calcite anchor; the scav_rat flat band **25/32/100×** (+0.01/+0.02/+0.05
log-MSE); and the three Track-2 failure modes (observability / support / structural). **If those
numbers change, update the `.tex` — the figures are the source of truth for the paper, so they must
track the record.**
