# Python's answers, for the differential unit tests

Each file holds CPython 3.13's answers for inputs its script generates.
The tests compare the Rust code against them.

| File | Script | Answers | Kept |
|---|---|---|---|
| `json.tsv` | `mkjson.py` | `json.loads` | every 8th line |
| `shlex.jsonl` | `mkshlex.py` | `shlex.split` | every 18th line |
| `intset.tsv` | `mkintset.py` | `set` iteration order | every 100th line |

To regenerate a file, run its script with Python 3.13 and keep the same lines:

```sh
python3.13 mkjson.py | awk 'NR%8==1' > json.tsv
```

To run against a script's whole output, set `JSON_CORPUS`, `SHLEX_CORPUS` or
`INTSET_CORPUS` to the file's path.

`storage/` holds tool output (smartctl, iSmart, SmartCmd) for the SSD
parsers in `src/storage.rs`. The tests compare against Python's `SsdUtil`
reading the same output. The `fx_*` files were captured for vendors and
error cases that `tests/test_ssd.py` does not cover. The rest are that test's
own outputs.
