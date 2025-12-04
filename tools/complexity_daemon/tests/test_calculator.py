"""Tests for the complexity calculator."""

import unittest
import tempfile
import os
from tools.complexity_daemon.calculator import calculate_complexity

class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file_path = os.path.join(self.temp_dir, "test.py")

    def tearDown(self):
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)
        os.rmdir(self.temp_dir)

    def _write_file(self, content):
        with open(self.test_file_path, "w") as f:
            f.write(content)

    def test_simple_function(self):
        """Test a simple function with one path."""
        self._write_file("def func_a():\\n    pass")
        self.assertEqual(calculate_complexity(self.test_file_path), 1)

    def test_if_statement(self):
        """Test a function with an if/else block."""
        self._write_file("def func_b(a, b):\\n    if a > b:\\n        return a\\n    else:\\n        return b")
        self.assertEqual(calculate_complexity(self.test_file_path), 2)

    def test_for_loop(self):
        """Test a function with a for loop."""
        self._write_file("def func_c(items):\\n    for item in items:\\n        print(item)")
        self.assertEqual(calculate_complexity(self.test_file_path), 2)

    def test_multiple_functions(self):
        """Test a file with multiple functions."""
        content = "def func_d():\\n    pass\\n\\ndef func_e():\\n    pass"
        self._write_file(content)
        # lizard gives a total complexity for the file
        self.assertEqual(calculate_complexity(self.test_file_path), 2)

    def test_empty_file(self):
        """Test an empty file."""
        self._write_file("")
        self.assertEqual(calculate_complexity(self.test_file_path), 0)

    def test_file_with_syntax_error(self):
        """Test a file with a syntax error."""
        self._write_file("def func_f(:")
        # lizard often returns 0 or 1 for files it can't parse properly
        self.assertIn(calculate_complexity(self.test_file_path), [0, 1])

    def test_non_existent_file(self):
        """Test a non-existent file."""
        self.assertEqual(calculate_complexity("non_existent_file.py"), 0)

    def test_unsupported_language(self):
        """Test a file with an unsupported language extension."""
        unsupported_file = os.path.join(self.temp_dir, "test.txt")
        with open(unsupported_file, "w") as f:
            f.write("some text")
        self.assertEqual(calculate_complexity(unsupported_file), 0)

if __name__ == "__main__":
    unittest.main()
