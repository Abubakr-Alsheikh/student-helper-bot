import asyncio
import logging
import platform
import shutil
from moviepy.editor import *
from pdf2image import convert_from_path
import subprocess
import os
import tempfile
import cv2
from docxtpl import DocxTemplate

logger = logging.getLogger(__name__)

async def generate_word_doc(template_path, output_path, quiz_data):
    """Generates the Word document."""
    try:
        doc = DocxTemplate(template_path)
        doc.render({"questions": quiz_data})
        doc.save(output_path)
    except Exception as e:
        logger.error(f"Error generating Word document: {e}")
        raise


async def convert_to_pdf(word_file, pdf_file=None):
    # Set default output name if pdf_file is not specified
    if pdf_file is None:
        pdf_file = os.path.splitext(word_file)[0] + ".pdf"

    # Set a temporary directory for the output to handle custom names
    temp_dir = os.path.dirname(pdf_file)
    temp_pdf_path = os.path.join(
        temp_dir, os.path.splitext(os.path.basename(word_file))[0] + ".pdf"
    )

    if platform.system() == "Windows":
        soffice_path = r"C:\Program Files\LibreOffice\program\soffice"
    else:
        soffice_path = "libreoffice"
    # Run the LibreOffice command to convert to PDF in temp directory
    try:
        proc = await asyncio.create_subprocess_exec(
                soffice_path,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                temp_dir, # Use absolute path
                word_file, # Use absolute path
            )
        await proc.communicate()
    except subprocess.CalledProcessError as e:
        logger.error(f"LibreOffice conversion failed: {e}")
        logger.error(f"Return code: {e.returncode}")
        logger.error(f"stderr: {e.stderr}")  # Print the error output from LibreOffice!
        return None
    except FileNotFoundError as e:
        logger.error(f"File not found during conversion: {e}")
        return None
    # Rename to the specified pdf_file name if it differs from temp_pdf_path
    if os.path.exists(temp_pdf_path):
        if temp_pdf_path != pdf_file:
            shutil.move(temp_pdf_path, pdf_file)
        print(f"Conversion successful: {pdf_file}")
        return pdf_file
    else:
        raise FileNotFoundError("PDF conversion failed.")



def convert_pptx_to_mp4(pptx_path, mp4_path, fps=0.5, dpi=300, image_format="png"):
    """
    Converts a PPTX file to an MP4 video by first converting it to a PDF,
    then converting each PDF page to an image, and finally combining
    the images into a video.

    Parameters:
    - pptx_path: Path to the input PPTX file
    - mp4_path: Path to the output MP4 file
    - fps: Frames per second for the output video
    - dpi: DPI setting for converting PDF to images
    - image_format: Format to save images (default is PNG)
    """

    # Step 1: Convert PPTX to PDF using LibreOffice
    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_filename = os.path.splitext(os.path.basename(pptx_path))[0] + ".pdf"
        pdf_path = os.path.join(temp_dir, pdf_filename)

        # Run the LibreOffice command to convert PPTX to PDF
        result = subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--invisible",
                "--convert-to",
                "pdf",
                "--outdir",
                temp_dir,
                pptx_path,
            ],
            check=True,
        )

        # Check if the PDF was created successfully
        if not os.path.exists(pdf_path):
            raise FileNotFoundError("PDF conversion failed.")
        print(f"Converted PPTX to PDF: {pdf_path}")

        # Step 2: Convert PDF to images
        images = convert_from_path(pdf_path, dpi=dpi, fmt=image_format)

        # Step 3: Save images to temporary files
        image_paths = []
        for i, img in enumerate(images):
            img_path = os.path.join(
                temp_dir, f"page_{str(i + 1).zfill(3)}.{image_format}"
            )
            img.save(img_path, image_format.upper())
            image_paths.append(img_path)

        print(f"PDF converted to images: {len(image_paths)} images generated.")

        # Step 4: Create video from images
        # Load first image to get frame dimensions
        frame = cv2.imread(image_paths[0])
        height, width, layers = frame.shape

        # Define the video codec and create VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # Codec for mp4
        video = cv2.VideoWriter(mp4_path, fourcc, fps, (width, height))

        # Add each image to the video
        for img_path in image_paths:
            frame = cv2.imread(img_path)
            video.write(frame)  # Write each image as a frame

        # Release the video writer
        video.release()
        print(f"Video saved as {mp4_path}")

    # Temporary files (PDF and images) are automatically deleted with temp_dir
