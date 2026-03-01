import sys
import unittest

from scripts.cli_common import ScriptCommand, build_common_args, normalize_app_name


class CliCommonTests(unittest.TestCase):
    def test_normalize_app_name_removes_spaces(self):
        self.assertEqual(normalize_app_name("My App Name"), "MyAppName")

    def test_build_common_args(self):
        self.assertEqual(
            build_common_args(app="DemoApp", root_dir="./tmp"),
            ("--app", "DemoApp", "--root_dir", "./tmp"),
        )

    def test_script_command_to_argv(self):
        command = ScriptCommand("scripts/task_executor.py", ("--app", "DemoApp"))
        self.assertEqual(
            command.to_argv(),
            [sys.executable, "scripts/task_executor.py", "--app", "DemoApp"],
        )


if __name__ == "__main__":
    unittest.main()
