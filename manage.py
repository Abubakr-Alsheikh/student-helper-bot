#!/usr/bin/env python
import argparse
import asyncio
import sys
from typing import Callable, Dict, Optional

from generating_verable_questions.get_questions_from_excel_as_json import generate_similar_questions_excel_batch


class CommandManager:
    def __init__(self):
        self.commands: Dict[str, Callable] = {}
        self.parser = argparse.ArgumentParser(description="Project management script")
        self.subparsers = self.parser.add_subparsers(
            dest="command", help="Available commands"
        )

    def register_command(
        self,
        name: str,
        handler: Callable,
        help_text: str,
        add_arguments: Optional[Callable] = None,
    ):
        """
        Register a new command with the manager.

        Args:
            name: Name of the command
            handler: Function to handle the command
            help_text: Description of what the command does
            add_arguments: Optional function to add command-specific arguments
        """
        self.commands[name] = handler
        command_parser = self.subparsers.add_parser(name, help=help_text)
        if add_arguments:
            add_arguments(command_parser)

    def execute(self):
        """Execute the command specified in command-line arguments."""
        args = self.parser.parse_args()
        if not args.command:
            self.parser.print_help()
            sys.exit(1)

        handler = self.commands.get(args.command)
        if handler:
            handler(args)
        else:
            print(f"Unknown command: {args.command}")
            sys.exit(1)


# Example command handlers
def finetune(args):
    from generating_verable_questions.get_questions_from_excel_as_json import (
        generate_fine_tuning_data,
    )

    generate_fine_tuning_data()


def create_db(args):
    # Import and run database creation logic
    from utils.database import create_tables

    create_tables()


def generate_verbal_questions(args):
    # Import and run question generation logic
    from utils.database import generate_question

    generate_question()


def create_context_files_command(args):
    """Creates context files from Excel data."""
    from utils.question_management import create_context_files
    from config import ARABIC_PARAGHRAPHS_MK_EXCEL_FILE, CONTEXT_DIRECTORY

    excel_file = ARABIC_PARAGHRAPHS_MK_EXCEL_FILE  # Access the excel_file argument
    output_dir = CONTEXT_DIRECTORY # Access the output_dir argument
    create_context_files(excel_file, output_dir)

def generate_questions_from_chatgpt(args):
    from generating_verable_questions.get_questions_from_excel_as_json import generate_similar_questions_excel
    from config import VERBAL_FILE
    from AIModels.chatgpt import get_chatgpt_instance
    import pandas as pd

    loop = asyncio.get_event_loop()

    excel_file = VERBAL_FILE

    chatgpt = get_chatgpt_instance()
    num_questions = args.num if hasattr(args, "num") else 1
    num_rows = args.row if hasattr(args, "row") else 0
    batch_size = args.batch_size if hasattr(args, "batch_size") else 10  # Set batch size


    try:
        if num_rows > 0:
            df = pd.read_excel(excel_file)
            test_df = df.head(num_rows)  # Use .head() to get the first rows

            # Create a temporary Excel file with the test data
            excel_file = "temp_test_data.xlsx"
            test_df.to_excel(excel_file, index=False)

        file_path="new_questions.xlsx"
        start_row = 0
        question_number = 1
        # Get the last generated question number to continue from
        try:
            if num_rows == 0:
                existing_df = pd.read_excel(file_path)
                last_question_number = existing_df["رقم السؤال"].max()
                start_row = len(existing_df) # Start from the next row
                question_number = last_question_number + 1  # Update question_number
        except (FileNotFoundError, KeyError):
            start_row = 0
            question_number = 1
        if batch_size == 0:
            new_excel_file = loop.run_until_complete(generate_similar_questions_excel(
                    excel_file,
                    chatgpt,
                    num_similar_questions=num_questions,
                    start_row=start_row,
                    question_number=question_number,
                    temperature=0.7,
                    max_tokens=1000,
                    file_path=file_path
                ))
        else:
            new_excel_file = loop.run_until_complete(generate_similar_questions_excel_batch(
                excel_file,
                chatgpt,
                num_similar_questions=num_questions,
                start_row=start_row,
                question_number=question_number,
                temperature=0.7,
                max_tokens=1000,
                file_path=file_path,
                batch_size=batch_size
            ))

        if new_excel_file:
            print(f"New questions saved to {new_excel_file}")
    except FileNotFoundError:
        print(f"Error: File {excel_file} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


# Add command-specific arguments
def setup_generate_questions_from_chatgpt_args(parser):
    parser.add_argument(
        "--num", type=int, default=1, help="Number of questions to generate"
    )
    parser.add_argument(
        "--row", type=int, default=0, help="Number of rows to take from the excel file to copy it"
    )
    parser.add_argument("--batch_size", type=int, default=10, help="Number of rows to process concurrently")


def main():
    manager = CommandManager()

    # Register commands with their handlers
    manager.register_command("finetune", finetune, "Run the fine-tuning process")

    manager.register_command("createdb", create_db, "Create the database")

    manager.register_command(
        "generate-verbal",
        generate_verbal_questions,
        "Putting the questions from excel file to database",
    )

    manager.register_command(
        "create-contexts",
        create_context_files_command,
        "Create context files from Excel",
    )

    manager.register_command(
        "generate-questions",
        generate_questions_from_chatgpt,
        "Generate questions",
        setup_generate_questions_from_chatgpt_args,
    )

    # Execute the selected command
    manager.execute()


##### Example:
# python manage.py finetune
# python manage.py createdb
# python manage.py generate-verbal
# python manage.py generate-questions --num 20

if __name__ == "__main__":
    main()
