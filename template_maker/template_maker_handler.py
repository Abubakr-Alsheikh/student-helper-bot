from datetime import datetime
import os

from telegram import Update
from telegram.ext import CallbackContext
from template_maker.content_population import (
    find_expression,
    generate_number,
    replace_placeholders_in_powerpoint,
    replace_placeholders_in_word,
)
from template_maker.data_preparation import (
    load_powerpoint_template,
    read_excel_data,
)
from template_maker.file_exports import convert_docx_to_pdf, convert_pptx_to_mp4
from template_maker.q_and_a_update import q_and_a_document


def sanitize_folder_name(name):
    """Removes invalid characters from folder names."""
    return "".join(char for char in name if char.isalnum() or char in " _-")


def create_folder_structure(df):
    """Creates the folder structure, populates templates, and exports files."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_folder = os.path.join(script_dir, "Main_Classification_Structure")
    os.makedirs(main_folder, exist_ok=True)

    for main_class in df["التصنيف الرئيسي مدقق"].unique():
        main_class_folder = os.path.join(
            main_folder, sanitize_folder_name(main_class[:50])
        )
        os.makedirs(main_class_folder, exist_ok=True)

        sub_df = df[df["التصنيف الرئيسي مدقق"] == main_class]
        for sub_class_list in sub_df["التصنيفات الفرعية مدققة"].str.split(r"[،,]"):
            for sub_class in sub_class_list:
                sub_class_folder = os.path.join(
                    main_class_folder, sanitize_folder_name(sub_class.strip()[:50])
                )
                os.makedirs(sub_class_folder, exist_ok=True)

                filtered_df = sub_df[
                    sub_df["التصنيفات الفرعية مدققة"].str.contains(sub_class.strip())
                ]

                for index, row in filtered_df.iterrows():
                    model_number = index - filtered_df.index[0] + 1
                    model_folder = os.path.join(
                        sub_class_folder, f"نموذج {model_number}"
                    )
                    os.makedirs(model_folder, exist_ok=True)

                    number = generate_number()
                    expression_number = find_expression(number)

                    data = {
                        "studentName": "someone",
                        "number": number,
                        "expressionNumber": expression_number,
                        "modelNumber": model_number,
                        "date": datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
                        "questionsNumber": "31",
                        "studentsResults": "100%",
                        "question": row["نص السؤال مدقق"],
                    }

                    # --- Word Population ---
                    word_file_path = os.path.join(
                        model_folder, f"نموذج {model_number}.docx"
                    )
                    replace_placeholders_in_word(word_file_path, data)

                    # PowerPoint Population (similar logic)
                    powerpoint_template = load_powerpoint_template()
                    if powerpoint_template:
                        replace_placeholders_in_powerpoint(powerpoint_template, data)

                        # if row["اسم الصورة"]:
                        #     image_path = os.path.join(IMAGE_FOLDER, row["اسم الصورة"])
                        #     slide = powerpoint_template.slides[0]
                        #     # left = PtInches(1)
                        #     # top = PtInches(2)
                        #     # slide.shapes.add_picture(image_path, left, top)
                        #     slide.shapes.add_picture(image_path, 0, 0)

                        pptx_file_path = os.path.join(
                            model_folder, f"نموذج {model_number}.pptx"
                        )
                        powerpoint_template.save(pptx_file_path)

                    # --- File Exports ---
                    pdf_file_path = os.path.join(
                        model_folder, f"نموذج {model_number}.pdf"
                    )
                    convert_docx_to_pdf(word_file_path, pdf_file_path)

                    # # if powerpoint_template:

                    # #     mp4_file_path = os.path.join(
                    # #         model_folder, f"نموذج {model_number}.mp4"
                    # #     )
                    # #     convert_pptx_to_mp4(pptx_file_path, mp4_file_path)

                    # --- Q&A Population ---
                    # q_and_a_file_path = os.path.join(
                    #     model_folder, f"نموذج {model_number}.word"
                    # )
                    # q_and_a_document(df,q_and_a_file_path)

                    # # --- Q&A Exports ---
                    # pdf_file_path = os.path.join(
                    #     model_folder, f"نموذج {model_number}.pdf"
                    # )
                    # convert_docx_to_pdf(q_and_a_file_path, pdf_file_path)


async def template_maker(update: Update, context: CallbackContext):
    """Main function to execute the entire process."""
    df = read_excel_data()
    create_folder_structure(df)
