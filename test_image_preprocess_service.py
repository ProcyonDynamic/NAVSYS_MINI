from pathlib import Path
from modules.portalis_mini.intelligence.image_preprocess_service import preprocess_image, PreprocessOptions

source = Path(r"D:\NAVSYS_USB\sample_passport_page1.png")
output = Path(r"D:\NAVSYS_USB\tmp_test\preprocessed.png")

print("Exists:", source.exists())

result = preprocess_image(
    image_path=source,
    output_path=output,
    options=PreprocessOptions(save_debug_steps=True),
)

print("OK:", result.ok)
print("Steps:", result.steps_applied)
print("Diagnostics:", result.diagnostics)
print("Output file:", result.output_path)