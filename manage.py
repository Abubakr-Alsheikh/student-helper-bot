#!/usr/bin/env python
import argparse
import sys
from typing import Callable, Dict, Optional


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
    from utils.question_management import generate_verbal_questions

    generate_verbal_questions()


def generate_questions(args):
    # Import and run question generation logic
    num_questions = args.num if hasattr(args, "num") else 10
    generate_questions(num_questions)


# Add command-specific arguments
def setup_generate_questions_args(parser):
    parser.add_argument(
        "--num", type=int, default=10, help="Number of questions to generate"
    )


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
        "generate-questions",
        generate_questions,
        "Generate questions",
        setup_generate_questions_args,
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
