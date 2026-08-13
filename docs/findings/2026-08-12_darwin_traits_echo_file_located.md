# The `darwin_traits.txt` echo file is real, and it is written by the routine whose precedence we need to confirm

**Date:** 2026-08-12 · **Cost:** source read, no cluster · **Status:** mechanism confirmed at
primary source; the artifact itself is still not in hand, so **`ded215` stays open**

## Why this was looked for

Lauderdale, 2026-08-12: *"There may also be a file `darwin_traits` that is written out by the model
with the values it uses… not sure if that is included in the ECCO-Darwin repo/datastore."*

`ded215` is the one pending verification behind the rain-ratio precedence: the argument that
`data.traits` overrides `data.darwin` rests on **source read-order** plus the disagreement between
the two files, and has never been confirmed against a real run's own output. Jon named a cheaper
route than grepping `STDOUT.0000`.

## What the source says

`darwinproject/darwin3`, `pkg/darwin/darwin_init_fixed.F`, immediately before the traits read:

```fortran
      IF ( myProcId.EQ.0 .AND. myThid.EQ.1 ) THEN
        CALL MDSFINDUNIT( oUnit1, mythid )
        open(oUnit1,file='darwin_traits.txt',status='unknown')
      ELSE
        oUnit1 = -1
      ENDIF

      CALL DARWIN_READ_TRAITS(iUnit, oUnit1, myThid)

      IF ( oUnit1 .GE. 0 ) THEN
        close(oUnit1)
      ENDIF
```

**The file is `darwin_traits.txt`, and it is written by `DARWIN_READ_TRAITS` itself** — the output
unit is opened, handed to that routine, and closed immediately after it returns.

That is exactly the right instrument for `ded215`, and better than the STDOUT route. The precedence
question is *"does `DARWIN_READ_TRAITS` overwrite what `DARWIN_GENERATE_RANDOM` produced?"*, and this
file is that routine's own record of the values it loaded. A v05 `darwin_traits.txt` showing
`R_PICPOC = 0.0, 2*4.1886E-2, 4*0.0` would confirm the precedence from the model's own output rather
than from our reading of the call order.

Written only by `myProcId == 0 .AND. myThid == 1`, at initialisation, into the run directory.

## Status: still open, but now actionable

Searched `~/dd_data` on AICR (the v05 datastore we hold): **no `darwin_traits.txt`, and no
`STDOUT.*`.** We hold the model *outputs*, not the run directories, so neither confirmation route is
available from what is currently staged.

So `ded215` does not close today. What changes is that it moves from "no known route" to "known
route, exact filename, need one artifact" — a request that can be made in one line:

> Does any v05 `llc270` run directory still have its `darwin_traits.txt`?

That is a better question to put to Jon than the original, and it costs him a `ls` rather than a
code read.

## What this does NOT change

Nothing numerical. The precedence conclusion is unchanged and still rests on the source read-order
(`DARWIN_GENERATE_RANDOM` at line 361, `DARWIN_READ_TRAITS` at 389) plus the measured file
disagreement — now with Lauderdale's independent confirmation on top. The ~1.4% gap between the
published 0.04245 and the integrated 0.0418860 remains inside the 5% Excellent band, so no reported
number moves either way.
