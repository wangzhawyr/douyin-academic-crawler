# Examples

This folder contains local acceptance fixtures. They do not contact Douyin or
any other platform.

## Files

- `mock_comment_tree.json`: a four-level comment tree used by mock mode.
- `local_comment_tree_sample.json`: a four-level local JSON import sample.
- `sample_config.json`: a local configuration example with `mock_mode=true`.
- `local_json_config.json`: a local JSON import configuration example.

## Local Acceptance

Run one mock collection task without opening the GUI:

```powershell
python main.py --mock-run --config examples/sample_config.json
```

Run one local JSON import task:

```powershell
python main.py --mock-run --config examples/local_json_config.json
```

Expected outputs:

- `exports/comments/comments_video-fixture-001_depth4_task-*_YYYYMMDD.csv`
- `exports/audit/audit.jsonl`
- `exports/logs/runtime.log`

The default GUI mode also uses the same mock fixture client when
`mock_mode=true`.
