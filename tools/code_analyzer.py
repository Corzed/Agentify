# code_analyzer.py
import ast


def analyze_code(code):
    """
    Perform a simple analysis of Python code.
    """
    try:
        tree = ast.parse(code)

        analysis = {
            "num_functions": len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]),
            "num_classes": len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]),
            "num_imports": len([node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]),
            "num_variables": len([node for node in ast.walk(tree) if isinstance(node, ast.Assign)])
        }

        return f"Analysis results:\n" + "\n".join(f"{k}: {v}" for k, v in analysis.items())
    except SyntaxError as e:
        return f"Syntax error in the provided code: {str(e)}"


tool = {
    "name": "code_analyzer",
    "description": "Analyze Python code and provide basic metrics",
    "function": analyze_code
}