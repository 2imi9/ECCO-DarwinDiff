# Master comparison across all overnight sweeps

**Total config-groups:** 11
**Carroll-published R_PICPOC target:** 0.0425

## Ranked by (at_5, mean_cal, excellents)

| Config | n | at6 | at5 | at4 | mean | excs | alpfe | scav_rat | Smallgrow | Biggrow | diatomgraz | R_PICPOC | R_PIC mean | R_PIC range |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---|
| `[max-lever] picabs=0.5, pocabs=0.25, posi=1.0, fco2=0.01, chl1W=3.0, mehrbach` | 15 | 0 | 0 | 4 | 2.93 | 3 | 0 | 0 | 10 | 15 | 4 | 15 | 0.0339 | 0.0286–0.0390 |
| `[modis-lowW] posi=1.0, modis=0.1` | 10 | 0 | 0 | 0 | 2.40 | 7 | 3 | 7 | 8 | 5 | 1 | 0 | 0.0157 | 0.0113–0.0183 |
| `[max-lever] picabs=0.5, pocabs=0.25, posi=1.0, fco2=0.01, mehrbach` | 20 | 0 | 0 | 0 | 2.30 | 1 | 0 | 0 | 6 | 20 | 0 | 20 | 0.0347 | 0.0290–0.0399 |
| `[modis-W1] pocabs=0.25, posi=1.0, modis=1.0` | 10 | 0 | 0 | 0 | 1.90 | 1 | 0 | 0 | 9 | 10 | 0 | 0 | 0.2203 | 0.1924–0.2491 |
| `[modis-W1] pocabs=0.25, posi=1.0, modis=1.0, mehrbach` | 10 | 0 | 0 | 0 | 1.90 | 1 | 0 | 0 | 9 | 10 | 0 | 0 | 0.2203 | 0.1924–0.2491 |
| `[max-lever] picabs=0.5, pocabs=0.25, posi=1.0, fco2=0.01, mehrbach, mld` | 5 | 0 | 0 | 0 | 1.80 | 1 | 0 | 0 | 0 | 5 | 0 | 4 | 0.0357 | 0.0252–0.0438 |
| `[max-lever] picabs=0.5, pocabs=0.25, posi=1.0, fco2=0.01, mehrbach, cocco` | 5 | 0 | 0 | 0 | 1.80 | 0 | 0 | 0 | 5 | 4 | 0 | 0 | 0.2346 | 0.1801–0.3116 |
| `[modis-lowW] pocabs=0.25, posi=1.0, modis=0.01` | 10 | 0 | 0 | 0 | 1.60 | 3 | 0 | 0 | 6 | 10 | 0 | 0 | 0.1962 | 0.1054–0.2825 |
| `[modis-lowW] pocabs=0.25, posi=1.0, modis=0.1` | 10 | 0 | 0 | 0 | 1.60 | 3 | 0 | 0 | 6 | 10 | 0 | 0 | 0.2025 | 0.1420–0.2582 |
| `[modis-lowW] pocabs=0.25, posi=1.0, modis=0.3` | 10 | 0 | 0 | 0 | 1.60 | 2 | 0 | 0 | 7 | 9 | 0 | 0 | 0.2110 | 0.1695–0.2385 |
| `[modis-W1] posi=1.0, modis=1.0` | 10 | 0 | 0 | 0 | 1.30 | 2 | 0 | 0 | 1 | 2 | 0 | 10 | 0.0376 | 0.0261–0.0507 |

## Notes

- `R_PIC mean` is the mean joint-recovered R_PICPOC across seeds. Carroll target = 0.0425.
- Per-parameter columns are #seeds at Cal-grade or Excellent out of n.
Traceback (most recent call last):
  File "C:\Users\Frank\OneDrive\Desktop\Github\ecco-darwindiff\.claude\worktrees\musing-gauss-962009\scripts\compare_all_sweeps.py", line 176, in <module>
    main()
  File "C:\Users\Frank\OneDrive\Desktop\Github\ecco-darwindiff\.claude\worktrees\musing-gauss-962009\scripts\compare_all_sweeps.py", line 171, in main
    print("- Sweep labels: max-lever (Darwin v05 PIC), modis-W1 (MODIS PIC weight=1.0), "
  File "C:\Users\Frank\AppData\Local\Programs\Python\Python311\Lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'charmap' codec can't encode character '\u2208' in position 106: character maps to <undefined>
