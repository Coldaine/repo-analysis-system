import unittest
import os
from tools.complexity_daemon.calculator import calculate_complexity

class TestCalculator(unittest.TestCase):
    def test_calculate_complexity(self):
        # Create a dummy python file
        with open("test.py", "w") as f:
            f.write("def foo(a, b):\n")
            f.write("    if a > b:\n")
            f.write("        return a\n")
            f.write("    else:\n")
            f.write("        return b\n")

        complexity = calculate_complexity("test.py")
        self.assertEqual(complexity, 2)

        os.remove("test.py")

if __name__ == "__main__":
    unittest.main()
