import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("permissions", Path(__file__).parents[1] / "starter/setup_permissions.py")
permissions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permissions)

class PermissionTests(unittest.TestCase):
    def test_private_settings_override_environment_assignments(self):
        settings = dict(KB_ID="ABCDEFGHIJ", MEMORY_ID="CustomerSupportMemory-ABCDEFGHIJ", REGION="us-east-1")
        source = 'import os\nKB_ID = os.environ.get("KB_ID", "")\n'
        self.assertEqual(permissions.read_settings(source, settings), settings)

    def test_policy_contains_scoped_interpreter_and_existing_integrations(self):
        policy = permissions.build_policy("aws", "123456789012",
            dict(KB_ID="ABCDEFGHIJ", MEMORY_ID="CustomerSupportMemory-ABCDEFGHIJ", REGION="us-east-1"))
        statement = next(s for s in policy["Statement"] if "bedrock-agentcore:InvokeCodeInterpreter" in s["Action"])
        self.assertTrue(statement["Resource"].endswith(":aws:code-interpreter/aws.codeinterpreter.v1"))
        self.assertTrue(any(s["Action"] == "bedrock:Retrieve" for s in policy["Statement"]))
        self.assertFalse(any(s["Resource"] == "*" for s in policy["Statement"]))

if __name__ == "__main__":
    unittest.main()
