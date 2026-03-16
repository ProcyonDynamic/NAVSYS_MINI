from pdf2image import convert_from_path

pdf_path = r"D:\NAVSYS_USB\data\PORTALIS\test_docs\passport_sample.pdf"

images = convert_from_path(pdf_path)

images[0].save(r"D:\NAVSYS_USB\sample_passport_page1.png")

print("Created sample_passport_page1.png")