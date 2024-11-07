import asyncio
import pandas as pd
import json
import os

from AIModels.chatgpt import get_chatgpt_instance
from config import CONTEXT_DIRECTORY, VERBAL_FILE


def read_context_from_folder(folder_path, context_name):
    """
    Reads context from a text file in the specified folder if the file matches the context name.
    Returns the context content if found; otherwise, returns 'N/A'.
    """
    context_file_path = os.path.join(folder_path, f"{context_name}.txt")
    if os.path.isfile(context_file_path):
        with open(context_file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "N/A"


def prepare_fine_tuning_data(excel_file, context_folder):
    """
    Reads the Excel file and formats data for fine-tuning to create unique questions in each given category,
    checking for context in specified folder based on column data.
    """
    try:
        df = pd.read_excel(excel_file)
        fine_tuning_data = []

        for _, row in df.iterrows():
            # Extract row data, removing any extra prefixes for clean output
            if not pd.notna(row["القطعة"]):
                continue
            main_category = row["التصنيف الرئيسي"]
            question_text = row["نص السؤال"]
            option_a = row["الخيار أ"]
            option_b = row["الخيار ب"]
            option_c = row["الخيار ج"]
            option_d = row["الخيار د"]
            explanation = row["الشرح"]
            correct_answer = row["الجواب الصحيح"]
            context_name = row["القطعة"] if pd.notna(row["القطعة"]) else "N/A"

            # Retrieve the actual context content if a context name is provided
            passage_context = read_context_from_folder(context_folder, context_name)

            # Example-based prompt for generating a unique question
            prompt = f"""
            Create a unique Arabic question in the '{main_category}' category for the context '{context_name}'.
            Context details: {passage_context}
            - Provide four answer options (A, B, C, D) with one correct answer.
            - Format the response in JSON format to match the following structure.
            - Include the correct answer and an explanation in Arabic.
            """

            # Define example answer structure to model output format
            example_answer = {
                "نص السؤال": question_text,
                "الخيار أ": option_a,
                "الخيار ب": option_b,
                "الخيار ج": option_c,
                "الخيار د": option_d,
                "الشرح": explanation,
                "التصنيف الرئيسي": main_category,
                "الجواب الصحيح": correct_answer,
                "القطعة": context_name,
            }

            # Prepare the fine-tuning input, with roles for system, user, and assistant
            fine_tuning_example = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a question generator for Arabic verbal reasoning tests, tasked with creating unique questions per specified category.",
                    },
                    {"role": "user", "content": prompt},
                    {
                        "role": "assistant",
                        "content": json.dumps(example_answer, ensure_ascii=False),
                    },
                ]
            }
            fine_tuning_data.append(fine_tuning_example)

        # Save formatted fine-tuning data to JSONL file
        with open(
            "fine_tuning_data_verbal_questions.jsonl", "w", encoding="utf-8"
        ) as f:
            for example in fine_tuning_data:
                json.dump(example, f, ensure_ascii=False)
                f.write("\n")  # New line for JSONL format

        print("Fine-tuning data saved to fine_tuning_data_verbal_questions.jsonl")
        return "fine_tuning_data_verbal_questions.jsonl"

    except FileNotFoundError:
        print(f"Error: File {excel_file} not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


async def generate_similar_questions_excel(
    excel_file,
    chatgpt_instance,
    num_similar_questions=1,
    start_row=0,
    question_number=1,
    file_path="new_questions.xlsx",
    **kwargs,
):
    """Generates similar questions using ChatGPT and formats them for Excel."""
    try:
        df = pd.read_excel(excel_file)
        new_questions = []

        for index, row in df.iloc[start_row:].iterrows():
            if not pd.notna(row["القطعة"]):
                continue
            if row['التصنيف الرئيسي'] == "استيعاب المقروء":
                print("It get to 'استيعاب المقروء' the file has finished")
                break
            try:
                # Prepare the prompt for ChatGPT
                prompt = f"""
                Generate {num_similar_questions} similar questions with distinct text and new answer options.
                Crucially, maintain the same underlying logical relationship as the example.
                Create new answer options and a distinct question text. Ensure all answer choices are varied, plausible, and relevant.
                Include the correct answer and explanation in Arabic, but keep the explanation as is.

                Main Category: {row['التصنيف الرئيسي']}
                Example Question: {row['نص السؤال']}
                Logical Relationship: {row['الشرح']}  <-- This is KEY

                Example Options:
                A) {row['الخيار أ']}
                B) {row['الخيار ب']}
                C) {row['الخيار ج']}
                D) {row['الخيار د']}

                Correct Example Option: {row["الجواب الصحيح"]}
                Explaintion: {row['الشرح']}

                Sub-Category:  [Generate a relevant sub-category based on the main category and logical relationship.]

                Return the generated questions as a JSON array of objects, where each object has the following keys:
                "نص السؤال", "الخيار أ", "الخيار ب", "الخيار ج", "الخيار د", "الشرح", "التصنيف الرئيسي", "الجواب الصحيح", "القطعة"

                Example JSON Output (for one generated question):
                [
                    {{"نص السؤال": "...", "الخيار أ": "...", "الخيار ب": "...", "الخيار ج": "...", "الخيار د": "...", "الشرح": "...", "التصنيف الرئيسي": "{row['التصنيف الرئيسي']}", "التصنيف الفرعي": "...", "الجواب الصحيح": "...", "القطعة": "{row['القطعة']}"}}
                ]

                Include a "التصنيف الفرعي" (Sub-Category) key in each object, and saperate the sub categoies by commans. Just remember dont add "Response: ```json" just return the response as JSON
                """

                system_message = "You are an assistant specialized in creating Arabic verbal reasoning questions with specific logical structures and relevant sub-categories."
                # Request ChatGPT to generate responses
                assistant_response = await chatgpt_instance.generate_response(
                    [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt},
                    ],
                    **kwargs,
                )

                if assistant_response:
                    try:
                        # Load the response JSON and check if it's a list (multiple questions)
                        response_json = json.loads(assistant_response)
                        if isinstance(response_json, list):
                            # If the response is a list, add each question to new_questions
                            for question in response_json:
                                question["رقم السؤال"] = question_number # Add question number
                                new_questions.append(question)
                                question_number += 1
                        else:
                            # If it's a single object, add it as one question
                            response_json["رقم السؤال"] = question_number
                            new_questions.append(response_json)
                            question_number += 1

                        print(f"The line {index + 1} has finished")

                    except json.JSONDecodeError as e:
                        print(f"JSON decoding error at row {index + 1}: {e}")
                        print(f"Response: {assistant_response}")
                        break
                else:
                    break
            except Exception as e:  # Catch any other errors during generation
                print(f"Error processing row {index + 1}: {e}")
                break

        # Convert the new questions to a DataFrame
        new_df = pd.DataFrame(new_questions)

        # Check if the file already exists
        if os.path.exists(file_path):
            # If file exists, load existing data and append new questions
            existing_df = pd.read_excel(file_path)
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            # If file does not exist, use the new DataFrame as the updated DataFrame
            updated_df = new_df

        # Save the updated DataFrame back to the Excel file
        updated_df.to_excel(file_path, index=False)
        print(f"Questions saved to {file_path}")
        return file_path
    except FileNotFoundError:
        print(f"Error: File {excel_file} not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


async def generate_similar_questions_batch(chatgpt_instance, rows, num_similar_questions, question_number, **kwargs):
    """Generate similar questions for a batch of rows."""
    tasks = []
    for index, row in rows.iterrows():
        # Prepare the prompt for each question
        if not pd.notna(row["القطعة"]):
            continue
        if row['التصنيف الرئيسي'] == "استيعاب المقروء":
            return None
        prompt = f"""
        Generate {num_similar_questions} similar questions with distinct text and new answer options.
        Crucially, maintain the same underlying logical relationship as the example.
        Create new answer options and a distinct question text. Ensure all answer choices are varied, plausible, and relevant.
        Include the correct answer and explanation in Arabic, but keep the explanation as is.

        Main Category: {row['التصنيف الرئيسي']}
        Example Question: {row['نص السؤال']}
        Logical Relationship: {row['الشرح']}  <-- This is KEY

        Example Options:
        A) {row['الخيار أ']}
        B) {row['الخيار ب']}
        C) {row['الخيار ج']}
        D) {row['الخيار د']}

        Correct Example Option: {row["الجواب الصحيح"]}
        Explaintion: {row['الشرح']}

        Sub-Category:  [Generate a relevant sub-category based on the main category and logical relationship and question, and the specific Arabic grammatical concepts used in the example question. Provide only grammatically relevant sub-categories. Be specific and use Arabic grammar terminology.]

        Return the generated questions as a JSON array of objects, where each object has the following keys:
        "نص السؤال", "الخيار أ", "الخيار ب", "الخيار ج", "الخيار د", "الشرح", "التصنيف الرئيسي", "الجواب الصحيح", "القطعة"

        Example JSON Output (for one generated question):
        [
            {{"نص السؤال": "...", "الخيار أ": "...", "الخيار ب": "...", "الخيار ج": "...", "الخيار د": "...", "الشرح": "...", "التصنيف الرئيسي": "{row['التصنيف الرئيسي']}", "التصنيف الفرعي": "...", "الجواب الصحيح": "...", "القطعة": "{row['القطعة']}"}}
        ]

        Include a "التصنيف الفرعي" (Sub-Category) key in each object, and saperate the sub categoies by commans. Just remember dont add "Response: ```json" just return the response as JSON
        """
        # System message as before
        system_message = "You are an assistant specialized in creating Arabic verbal reasoning questions with specific logical structures and relevant sub-categories. You have a deep understanding of Arabic grammar."

        # Create a task for each question generation call
        tasks.append(chatgpt_instance.generate_response(
            [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            **kwargs
        ))

    responses = await asyncio.gather(*tasks)  # Run all tasks concurrently
    questions = []
    for assistant_response in responses:
        if assistant_response:
            try:
                response_json = json.loads(assistant_response)
                if isinstance(response_json, list):
                    for question in response_json:
                        question["رقم السؤال"] = question_number
                        questions.append(question)
                        question_number += 1
                else:
                    response_json["رقم السؤال"] = question_number
                    questions.append(response_json)
                    question_number += 1
            except json.JSONDecodeError as e:
                print(f"JSON decoding error: {e}")
                continue
    return questions


async def generate_similar_questions_excel_batch(
    excel_file,
    chatgpt_instance,
    num_similar_questions=1,
    start_row=0,
    question_number=1,
    file_path="new_questions.xlsx",
    batch_size=10,  # Number of rows to process concurrently
    **kwargs,
):
    """Generates similar questions in batches and saves them to Excel."""
    df = pd.read_excel(excel_file)
    new_questions = []

    # Process rows in batches
    for i in range(start_row, len(df), batch_size):
        batch_rows = df.iloc[i:i+batch_size]
        questions = await generate_similar_questions_batch(
            chatgpt_instance, batch_rows, num_similar_questions, question_number, **kwargs
        )
        if questions:
            new_questions.extend(questions)
            question_number += len(questions)
            print(f"Processed batch starting from row {i + 1}")
        else:
            print("Reached 'استيعاب المقروء'. File processing complete.")
            break

    # Save new questions to the Excel file
    new_df = pd.DataFrame(new_questions)
    if os.path.exists(file_path):
        existing_df = pd.read_excel(file_path)
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        updated_df = new_df

    updated_df.to_excel(file_path, index=False)
    print(f"Questions saved to {file_path}")
    return file_path

async def generate_custom_questions_by_category(
    category: str,
    passage: str,
    chatgpt_instance,
    context_folder,
    num_questions: int = 1,
    file_path="custom_questions_by_category.xlsx",
    **kwargs,
):
    """Generates unique questions within a specified category using the fine-tuned model."""
    new_questions = []

    # Retrieve the actual context content if a context name is provided
    passage_context = read_context_from_folder(context_folder, passage)

    for _ in range(num_questions):
        # Prepare the prompt for ChatGPT
        prompt = f"""
        Generate {num_questions} unique questions within the category "{category}" based on the following context '{passage}'..
        Passage/Context: {passage_context}
        Create new answer options, a distinct question text, and ensure all answer choices are varied and relevant.
        Include correct answer and explanation in Arabic.

        And if there is more than one question provide all questions in a structured JSON format as a list of objects.
        """

        system_message = "You are a question generator for Arabic verbal reasoning tests, tasked with creating unique questions per specified category."

        # Request ChatGPT to generate a unique question
        assistant_response = await chatgpt_instance.generate_response(
            [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            **kwargs,
        )

        if assistant_response:
            try:
                # Load the response JSON and check if it's a list (multiple questions)
                response_json = json.loads(assistant_response)
                if isinstance(response_json, list):
                    # If the response is a list, add each question to new_questions
                    for question in response_json:
                        new_questions.append(question)
                else:
                    # If it's a single object, add it as one question
                    new_questions.append(response_json)
            except json.JSONDecodeError as e:
                print(f"JSON decoding error: {e}")
                print(f"Response: {assistant_response}")

    # Convert the new questions to a DataFrame
    new_df = pd.DataFrame(new_questions)

    # Check if the file already exists
    if os.path.exists(file_path):
        # If file exists, load existing data and append new questions
        existing_df = pd.read_excel(file_path)
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        # If file does not exist, use the new DataFrame as the updated DataFrame
        updated_df = new_df

    # Save the updated DataFrame back to the Excel file
    updated_df.to_excel(file_path, index=False)
    print(f"Questions saved to {file_path}")
    return file_path


def generate_fine_tuning_data():
    excel_file = VERBAL_FILE  # Replace with your file's path
    jsonl_file = prepare_fine_tuning_data(excel_file, CONTEXT_DIRECTORY)


def generate_verbel_questions_with_excel_data():
    loop = asyncio.get_event_loop()

    excel_file = VERBAL_FILE  # Replace with your file's path

    chatgpt = get_chatgpt_instance()

    try:
        df = pd.read_excel(excel_file)
        # Process only the first 5 rows for testing
        test_df = df.head(10)  # Use .head() to get the first 5 rows

        # Create a temporary Excel file with the test data
        temp_excel = "temp_test_data.xlsx"
        test_df.to_excel(temp_excel, index=False)

        new_excel_file = loop.run_until_complete(
            generate_similar_questions_excel(
                temp_excel,
                chatgpt,
                num_similar_questions=2,
                temperature=0.7,
                max_tokens=500,
            )
        )

        if new_excel_file:
            print(f"New questions (test run) saved to {new_excel_file}")

    except FileNotFoundError:
        print(f"Error: File {excel_file} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def generate_verbel_questions_with_category():
    loop = asyncio.get_event_loop()

    chatgpt = get_chatgpt_instance()

    try:
        # Generate custom questions for a specific category
        category = "التناظر اللفظي"
        passage = "-"  # Replace with specific context if needed
        num_questions = 2  # Number of unique questions to generate

        new_excel_file = loop.run_until_complete(
            generate_custom_questions_by_category(
                category,
                passage,
                chatgpt,
                CONTEXT_DIRECTORY,
                num_questions,
                temperature=0.7,
                max_tokens=500,
            )
        )

        print(f"Generated questions saved to {new_excel_file}")

    except Exception as e:
        print(f"An error occurred: {e}")
