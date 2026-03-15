# test_image_preprocess_service.py
from pathlib import Path
from image_preprocess_service import preprocess_image, PreprocessOptions

sample = Path("sample_scan.jpg")
out = Path("tmp_portalis/preprocessed/sample_scan_preprocessed.png")

result = preprocess_image(
    image_path=sample,
    output_path=out,
    options=PreprocessOptions(
        save_debug_steps=True,
        adaptive_binarize=False,
    )
)

print("OK:", result.ok)
print("OUT:", result.output_path)
print("STEPS:", result.steps_applied)
print("DIAG:", result.diagnostics)