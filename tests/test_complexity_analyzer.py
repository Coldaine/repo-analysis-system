"""
Unit tests for ComplexityAnalyzer
"""

import os
import tempfile
import unittest
from pathlib import Path

from src.analysis.complexity_analyzer import (
    ComplexityAnalyzer,
    ComplexityReport,
    FileComplexity,
    FunctionComplexity,
    ComplexityMetrics,
)


class TestComplexityAnalyzer(unittest.TestCase):
    """Test cases for ComplexityAnalyzer"""

    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = ComplexityAnalyzer(hotspot_threshold=10)
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_test_file(self, filename: str, content: str) -> str:
        """Helper to create a test Python file"""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(content)
        return filepath

    def test_simple_function_complexity(self):
        """Test complexity calculation for a simple function"""
        code = """
def simple_function():
    return 1
"""
        filepath = self._create_test_file("simple.py", code)
        result = self.analyzer.analyze_file(filepath)

        self.assertIsInstance(result, FileComplexity)
        self.assertEqual(len(result.functions), 1)
        self.assertEqual(result.functions[0].name, "simple_function")
        self.assertEqual(result.functions[0].complexity, 1)
        self.assertFalse(result.functions[0].is_hotspot)

    def test_complex_function_hotspot(self):
        """Test complexity hotspot identification"""
        code = """
def complex_function(x):
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    if x > 40:
                        if x > 50:
                            return "very high"
                        return "high"
                    return "medium-high"
                return "medium"
            return "low-medium"
        return "low"
    return "negative"
"""
        filepath = self._create_test_file("complex.py", code)
        result = self.analyzer.analyze_file(filepath)

        self.assertEqual(len(result.functions), 1)
        func = result.functions[0]
        self.assertGreater(func.complexity, 10)
        self.assertTrue(func.is_hotspot)
        self.assertGreater(func.nesting_depth, 0)

    def test_multiple_functions(self):
        """Test analysis of file with multiple functions"""
        code = """
def func1():
    return 1

def func2(x):
    if x > 0:
        return x
    return 0

def func3(a, b, c):
    if a:
        if b:
            if c:
                return a + b + c
    return 0
"""
        filepath = self._create_test_file("multiple.py", code)
        result = self.analyzer.analyze_file(filepath)

        self.assertEqual(len(result.functions), 3)
        self.assertEqual(result.functions[0].name, "func1")
        self.assertEqual(result.functions[1].name, "func2")
        self.assertEqual(result.functions[2].name, "func3")

    def test_maintainability_index(self):
        """Test maintainability index calculation"""
        code = """
def well_structured():
    x = 1
    y = 2
    return x + y
"""
        filepath = self._create_test_file("maintainable.py", code)
        result = self.analyzer.analyze_file(filepath)

        self.assertGreater(result.maintainability_index, 0)
        self.assertIsNotNone(result.maintainability_rank)

    def test_nesting_depth_calculation(self):
        """Test nesting depth calculation"""
        code = """
def nested_function(x):
    if x > 0:
        for i in range(x):
            while i > 0:
                if i % 2 == 0:
                    return i
                i -= 1
    return 0
"""
        filepath = self._create_test_file("nested.py", code)
        result = self.analyzer.analyze_file(filepath)

        func = result.functions[0]
        self.assertGreater(func.nesting_depth, 2)

    def test_repository_analysis(self):
        """Test analysis of entire repository"""
        # Create multiple Python files
        self._create_test_file("file1.py", "def func1(): return 1")
        self._create_test_file("file2.py", "def func2(x): return x if x > 0 else 0")

        report = self.analyzer.analyze_repository(self.temp_dir)

        self.assertIsInstance(report, ComplexityReport)
        self.assertIsInstance(report.metrics, ComplexityMetrics)
        self.assertGreaterEqual(len(report.files), 2)
        self.assertEqual(report.metrics.total_files, len(report.files))

    def test_complexity_distribution(self):
        """Test complexity distribution histogram"""
        # Create files with varying complexity
        simple_code = "def simple(): return 1"
        complex_code = """
def complex(x):
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    if x > 40:
                        return "high"
    return "low"
"""
        self._create_test_file("simple.py", simple_code)
        self._create_test_file("complex.py", complex_code)

        report = self.analyzer.analyze_repository(self.temp_dir)

        self.assertIsNotNone(report.metrics.complexity_distribution)
        self.assertIn('A (1-5)', report.metrics.complexity_distribution)
        self.assertIn('B (6-10)', report.metrics.complexity_distribution)
        self.assertIn('C (11-20)', report.metrics.complexity_distribution)

    def test_hotspot_identification(self):
        """Test that hotspots are correctly identified and sorted"""
        code = """
def hotspot1(x):
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    if x > 40:
                        return "hotspot"
    return "normal"

def hotspot2(y):
    if y:
        if y > 1:
            if y > 2:
                if y > 3:
                    if y > 4:
                        if y > 5:
                            return "bigger hotspot"
    return "normal"

def simple():
    return 1
"""
        self._create_test_file("hotspots.py", code)

        report = self.analyzer.analyze_repository(self.temp_dir)

        # Should have 2 hotspots (complexity > 10)
        hotspots = [h for h in report.hotspots if h[1].complexity > 10]
        self.assertGreater(len(hotspots), 0)

        # Hotspots should be sorted by complexity (descending)
        if len(hotspots) > 1:
            for i in range(len(hotspots) - 1):
                self.assertGreaterEqual(
                    hotspots[i][1].complexity,
                    hotspots[i + 1][1].complexity
                )

    def test_empty_file(self):
        """Test analysis of empty file"""
        filepath = self._create_test_file("empty.py", "")
        result = self.analyzer.analyze_file(filepath)

        self.assertEqual(len(result.functions), 0)
        self.assertEqual(result.average_complexity, 0.0)
        self.assertEqual(result.max_complexity, 0)

    def test_file_with_classes(self):
        """Test analysis of file with class methods"""
        code = """
class MyClass:
    def method1(self):
        return 1

    def method2(self, x):
        if x > 0:
            return x
        return 0
"""
        filepath = self._create_test_file("classes.py", code)
        result = self.analyzer.analyze_file(filepath)

        # Should analyze methods as functions
        self.assertGreaterEqual(len(result.functions), 2)

    def test_raw_metrics(self):
        """Test raw metrics (LOC, LLOC, etc.)"""
        code = """
# This is a comment
def function():
    # Another comment
    x = 1  # Inline comment
    y = 2

    # More comments
    return x + y

# Final comment
"""
        filepath = self._create_test_file("metrics.py", code)
        result = self.analyzer.analyze_file(filepath)

        self.assertGreater(result.lines_of_code, 0)
        self.assertGreater(result.logical_lines, 0)
        self.assertGreater(result.comment_lines, 0)
        self.assertGreater(result.blank_lines, 0)

    def test_function_complexity_to_dict(self):
        """Test FunctionComplexity to_dict method"""
        func = FunctionComplexity(
            name="test_func",
            line_number=10,
            complexity=15,
            rank="C",
            nesting_depth=3,
            cognitive_complexity=18
        )

        result = func.to_dict()

        self.assertEqual(result['name'], "test_func")
        self.assertEqual(result['line_number'], 10)
        self.assertEqual(result['cyclomatic_complexity'], 15)
        self.assertEqual(result['rank'], "C")
        self.assertEqual(result['nesting_depth'], 3)
        self.assertEqual(result['cognitive_complexity'], 18)
        self.assertTrue(result['is_hotspot'])

    def test_file_complexity_to_dict(self):
        """Test FileComplexity to_dict method"""
        func = FunctionComplexity(
            name="test", line_number=1, complexity=5, rank="A"
        )
        file_comp = FileComplexity(
            file_path="/test/file.py",
            maintainability_index=75.5,
            maintainability_rank="A",
            functions=[func],
            lines_of_code=100,
        )

        result = file_comp.to_dict()

        self.assertEqual(result['file_path'], "/test/file.py")
        self.assertEqual(result['maintainability_index'], 75.5)
        self.assertEqual(result['lines_of_code'], 100)
        self.assertEqual(len(result['functions']), 1)

    def test_complexity_report_to_dict(self):
        """Test ComplexityReport to_dict method"""
        metrics = ComplexityMetrics(
            total_files=5,
            total_functions=20,
            total_hotspots=3,
            average_complexity=7.5
        )
        report = ComplexityReport(metrics=metrics, files=[], hotspots=[])

        result = report.to_dict()

        self.assertIn('metrics', result)
        self.assertIn('files', result)
        self.assertIn('hotspots', result)
        self.assertEqual(result['metrics']['total_files'], 5)


if __name__ == '__main__':
    unittest.main()
