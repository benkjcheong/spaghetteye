1. Give VSCode Local Network access

source .venv/bin/activate
python -m spaghettimonster

Optional AI spaghetti detection:

- Requires Bambu Studio installed locally so `libBambuSource.dylib` is present.
- Runs fully locally after the model file is downloaded once.
- Requires the printer liveview camera to be enabled on the printer.
- The A1 liveview path only supports one active client well, so close any competing liveview session first.
- On first use it downloads Obico's published ONNX failure-detection weights to `~/.cache/spaghettimonster/`.

Add these to `.env` to enable it:

```bash
SPAGHETTI_AI_ENABLED=true
SPAGHETTI_INTERVAL_SEC=30
SPAGHETTI_CONSECUTIVE_HITS=2
SPAGHETTI_MIN_CONFIDENCE=0.85
SPAGHETTI_DETECTION_THRESHOLD=0.08
# Optional override:
# CAMERA_LIBRARY_PATH=/Users/you/Library/Application Support/BambuStudio/plugins/libBambuSource.dylib
# SPAGHETTI_MODEL_PATH=/path/to/local/model.onnx
# SPAGHETTI_MODEL_URL=https://...
```
