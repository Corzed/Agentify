# calculator.py
import math

def calculate(expression):
    """
    Evaluate a mathematical expression.
    """
    try:
        # Use Python's eval function, but only allow safe operations
        allowed_names = {
            k: v for k, v in math.__dict__.items()
            if not k.startswith('__')
        }
        return eval(expression, {"__builtins__": None}, allowed_names)
    except Exception as e:
        return f"Error: {str(e)}"

tool = {
    "name": "calculator",
    "description": "Evaluate mathematical expressions",
    "function": calculate
}