from magic_pdf.pipe.UNIPipe import UNIPipe
from magic_pdf.rw.DiskReaderWriter import DiskReaderWriter
import os

def test():
    pdf_path = "test.pdf"
    if not os.path.exists(pdf_path):
        # Create a dummy PDF just to test import and object creation
        print("No test.pdf, but imports work.")
        return
    image_writer = DiskReaderWriter(os.path.dirname(pdf_path))
    pipe = UNIPipe(pdf_path, jso_useful_key={"_pdf_type": "", "model_list": []}, image_writer=image_writer)
    print("MinerU initialized successfully.")

test()
