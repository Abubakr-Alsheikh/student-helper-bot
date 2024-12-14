import itertools
import random

def generate_number():
    """Generate a 9-digit number."""
    digits = random.sample(range(10), 9)  # Ensure unique digits
    return "".join(map(str, digits))


def find_expression(number):
    """Find an expression that evaluates to 100."""
    digits = list(number)
    operators = ["+", "-", "*"]
    for perm in itertools.permutations(digits):  # Try all digit permutations
        for ops in itertools.product(
            operators, repeat=len(digits) - 1
        ):  # Try all operator combinations
            expression = ""
            for i, digit in enumerate(perm):
                expression += digit
                if i < len(perm) - 1:
                    expression += ops[i]

            try:
                if eval(expression) == 100:
                    return expression + " = 100"
            except (ZeroDivisionError, SyntaxError):
                pass  # Handle potential errors

    return "No solution found"  # If no solution is found
