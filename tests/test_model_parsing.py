import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
SCRIPTS_DIR = os.path.join(ROOT, 'scripts')
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

# Provide light stubs to avoid native dependency loading in utils.py imports.
if 'cv2' not in sys.modules:
    sys.modules['cv2'] = types.SimpleNamespace()
if 'pyshine' not in sys.modules:
    sys.modules['pyshine'] = types.SimpleNamespace()

import model  # noqa: E402


class ModelParsingTests(unittest.TestCase):
    def test_parse_explore_rsp_supports_multiline_fields(self):
        rsp = (
            "Observation:\n"
            "屏幕上有输入框和发送按钮\n"
            "Thought:\n"
            "需要先输入文本\n"
            "Action: text(\"hello\")\n"
            "Summary:\n"
            "已准备输入文本"
        )
        result = model.parse_explore_rsp(rsp)
        self.assertEqual(result[0], 'text')
        self.assertEqual(result[1], 'hello')

    def test_parse_reflect_rsp_supports_multiline_doc(self):
        rsp = (
            "Decision: CONTINUE\n"
            "Thought:\n"
            "动作有效\n"
            "Documentation:\n"
            "该按钮用于发送消息"
        )
        result = model.parse_reflect_rsp(rsp)
        self.assertEqual(result[0], 'CONTINUE')
        self.assertIn('发送消息', result[2])


if __name__ == '__main__':
    unittest.main()
