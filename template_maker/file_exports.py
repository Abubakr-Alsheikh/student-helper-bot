import asyncio
import logging
import platform
import shutil
from pdf2image import convert_from_path
import subprocess
import os
import tempfile
import cv2
from docxtpl import DocxTemplate
from pptx import Presentation
import time

if platform.system() == "Windows":
    import win32com.client

logger = logging.getLogger(__name__)

async def generate_word_doc(template_path, output_path, quiz_data):
    """Generates the Word document."""
    try:
        doc = DocxTemplate(template_path)
        doc.render(quiz_data)
        doc.save(output_path)
    except Exception as e:
        logger.error(f"Error generating Word document: {e}")
        raise


async def convert_docx_to_pdf(word_file, pdf_file=None):
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


async def generate_powerpoint(template_path, output_path, quiz_data):
    """
    Generates the PowerPoint presentation by duplicating the first four slides and replacing placeholders with data.
    
    Args:
        template_path (str): Path to the PowerPoint template file.
        output_path (str): Path to save the generated PowerPoint file.
        quiz_data (dict): Data containing the questions and related details.
    """
    try:
        # Load the PowerPoint template
        template_prs = Presentation(template_path)

        # Create a new presentation
        new_prs = Presentation()

        # Get the first four slides from the template
        template_slides = [template_prs.slides[i] for i in range(min(4, len(template_prs.slides)))]

        # Add slides for each question using the first 4 slides as templates
        for question_index, question in enumerate(quiz_data["questions"]):
            # Cycle through the 4 template slides
            template_slide = template_slides[question_index % 4]

            # Duplicate the slide
            slide = new_prs.slides.add_slide(template_slide.slide_layout)

            # Copy content from the template slide to the new slide
            for shape in template_slide.shapes:
                if shape.is_placeholder:
                    print(f"Placeholder name: {shape.name}, type: {shape.placeholder_format.type}")
                    try:
                        # Replace placeholders with actual content
                        placeholder_name = shape.text_frame.text
                        if "QuestionNumber" in placeholder_name:
                            shape.text_frame.text = str(question["QuestionNumber"])
                        elif "QuestionText" in placeholder_name:
                            shape.text_frame.text = question["QuestionText"]
                        elif "MainCategoryName" in placeholder_name:
                            shape.text_frame.text = question["MainCategoryName"]
                        elif "OptionA" in placeholder_name:
                            shape.text_frame.text = question["OptionA"]
                        elif "OptionB" in placeholder_name:
                            shape.text_frame.text = question["OptionB"]
                        elif "OptionC" in placeholder_name:
                            shape.text_frame.text = question["OptionC"]
                        elif "OptionD" in placeholder_name:
                            shape.text_frame.text = question["OptionD"]
                        elif "CorrectAnswer" in placeholder_name:
                            shape.text_frame.text = question["CorrectAnswer"]
                        elif "Explanation" in placeholder_name:
                            shape.text_frame.text = question["Explanation"]
                    except AttributeError:
                        # Handle shapes without text_frame (e.g., images or other elements)
                        continue

        # Save the modified PowerPoint presentation
        new_prs.save(output_path)

    except Exception as e:
        logger.error(f"Error generating PowerPoint: {e}")
        raise


async def convert_pptx_to_mp4(pptx_path, mp4_path, fps=0.5, dpi=300, image_format="png"):
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

        if platform.system() == "Windows":
            soffice_path = r"C:\Program Files\LibreOffice\program\soffice"
        else:
            soffice_path = "libreoffice"
        # Run the LibreOffice command to convert PPTX to PDF
        result = subprocess.run(
            [
                soffice_path,
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
        if platform.system() == "Windows":
            # Step 2: Convert PDF to images asynchronously
            images =  await asyncio.to_thread(convert_from_path,pdf_path, dpi=dpi, fmt=image_format, poppler_path=r"C:\poppler-24.08.0\Library\bin")
        else:
            images =  await asyncio.to_thread(convert_from_path,pdf_path, dpi=dpi, fmt=image_format)

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

def convert_pptx_to_mp4_with_windows(pptx_path, mp4_path, fps=0.5, dpi=300, image_format="png"):
    try:
        ppt = win32com.client.Dispatch('PowerPoint.Application')
        presentation = ppt.Presentations.Open(pptx_path, WithWindow=False)
        presentation.CreateVideo(mp4_path, -1, 4, 1080, 24, 60)
        start_time_stamp = time.time()

        while True:
            time.sleep(4)
            try:
                os.rename(mp4_path, mp4_path)
                print('Success')
                break
            except Exception as e:
                print(f"Waiting for video creation: {e}")

        end_time_stamp = time.time()
        print(end_time_stamp - start_time_stamp)
        presentation.Close()
        ppt.Quit()

    except Exception as e:
        print(f"Error in convert_pptx_to_mp4_with_windows: {e}")

async def convert_ppt_to_image(ppt_file_path, img_path, dpi=300, image_format="png"):
    """
    Converts a PPTX file to an image.
    """
    try:
        # Step 1: Convert PPTX to PDF using LibreOffice asynchronously
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_filename = os.path.splitext(os.path.basename(ppt_file_path))[0] + ".pdf"
            pdf_path = os.path.join(temp_dir, pdf_filename)

            if platform.system() == "Windows":
                soffice_path = r"C:\Program Files\LibreOffice\program\soffice"
            else:
                soffice_path = "libreoffice"
            # Run the LibreOffice command asynchronously
            cmd = [
                soffice_path,
                "--headless",
                "--invisible",
                "--convert-to",
                "pdf",
                "--outdir",
                temp_dir,
                ppt_file_path,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0 or not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF conversion failed: {stderr.decode()}")

            if platform.system() == "Windows":
                # Step 2: Convert PDF to images asynchronously
                images =  await asyncio.to_thread(convert_from_path,pdf_path, dpi=dpi, fmt=image_format, poppler_path=r"C:\poppler-24.08.0\Library\bin")
            else:
                images =  await asyncio.to_thread(convert_from_path,pdf_path, dpi=dpi, fmt=image_format)


            # Save the first page as the image for simplicity
            images[0].save(img_path, image_format.upper())

            return img_path

    except Exception as e:
        logger.error(f"Error converting PPTX to image: {e}")
        raise
