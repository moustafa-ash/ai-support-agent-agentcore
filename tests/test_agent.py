"""Offline tests of integration boundaries; these never call AWS or the model."""
import asyncio
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

os.environ.update(AWS_ACCESS_KEY_ID="offline-test", AWS_SECRET_ACCESS_KEY="offline-test",
                  AWS_EC2_METADATA_DISABLED="true", AWS_DEFAULT_REGION="us-east-1")
spec = importlib.util.spec_from_file_location("support_agent", Path(__file__).parents[1] / "starter/main.py")
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)

def message(role, text):
    return {"role": role, "content": [{"text": text}]}

class IntegrationTests(unittest.TestCase):
    def memory(self):
        client = MagicMock()
        client.get_memory_strategies.return_value = [
            {"type": "SEMANTIC", "namespaceTemplates": ["cs_agent/{actorId}/facts"]},
            {"memoryStrategyType": "USER_PREFERENCE", "namespaces": ["cs_agent/{actorId}/preferences"]},
        ]
        return client

    def test_namespaces_current_legacy_and_empty(self):
        client = self.memory()
        result = agent.get_namespaces(client, "memory")
        self.assertEqual(set(result), {"SEMANTIC", "USER_PREFERENCE"})
        client.get_memory_strategies.return_value = [{"type": "SEMANTIC"}]
        self.assertEqual(agent.get_namespaces(client, "memory"), {})

    def test_memory_retrieves_all_and_persists_original(self):
        client = self.memory()
        client.retrieve_memories.side_effect = [[{"content": {"text": "Name: Jane"}}],
                                                [{"content": {"text": "Concise answers"}}]]
        hook = agent.MemoryHook("CUST-123", "session", client, "memory")
        user = message("user", "Do you remember me?")
        state = SimpleNamespace(messages=[user])
        hook.retrieve_customer_context(SimpleNamespace(agent=state))
        self.assertIn("[SEMANTIC] Name: Jane", user["content"][0]["text"])
        self.assertIn("[USER_PREFERENCE] Concise answers", user["content"][0]["text"])
        self.assertEqual(client.retrieve_memories.call_count, 2)
        state.messages += [{"role": "user", "content": [{"toolResult": {}}]}, message("assistant", "Hi Jane!")]
        hook.save_support_interaction(SimpleNamespace(agent=state, result=object()))
        self.assertEqual(client.create_event.call_args.kwargs["messages"],
                         [("Do you remember me?", "USER"), ("Hi Jane!", "ASSISTANT")])

    def test_memory_actor_isolation_and_tool_results_ignored(self):
        client = self.memory()
        client.retrieve_memories.return_value = []
        for actor in ("CUST-123", "CUST-456"):
            hook = agent.MemoryHook(actor, "session", client, "memory")
            hook.retrieve_customer_context(SimpleNamespace(agent=SimpleNamespace(messages=[message("user", "Hi")])) )
            self.assertIn(actor, client.retrieve_memories.call_args.kwargs["namespace"])
        previous = client.retrieve_memories.call_count
        hook.retrieve_customer_context(SimpleNamespace(agent=SimpleNamespace(messages=[
            {"role": "user", "content": [{"text": "result"}, {"toolResult": {}}]}])))
        self.assertEqual(client.retrieve_memories.call_count, previous)
        hook.save_support_interaction(SimpleNamespace(result=None))
        client.create_event.assert_not_called()

    def test_rag_guard_empty_join_and_failure(self):
        with patch.object(agent, "KB_ID", ""):
            self.assertEqual(agent.search_knowledge_base("q"), "Knowledge base not configured.")
        with patch.object(agent, "KB_ID", "test"), patch.object(agent, "_bedrock_runtime") as runtime:
            runtime.retrieve.return_value = {"retrievalResults": [{"content": {"text": "first"}},
                                                                {"content": {"text": "second"}}]}
            self.assertEqual(agent.search_knowledge_base("q"), "first\n---\nsecond")
            runtime.retrieve.assert_called_with(knowledgeBaseId="test", retrievalQuery={"text": "q"},
                retrievalConfiguration={"managedSearchConfiguration": {"numberOfResults": 5}})
            runtime.retrieve.return_value = {"retrievalResults": []}
            self.assertIn("No relevant", agent.search_knowledge_base("q"))
            runtime.retrieve.side_effect = RuntimeError()
            self.assertIn("failed", agent.search_knowledge_base("q"))

    def calculate(self, points, tier, total, category="standard"):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(agent._discount_code(*agent._discount_inputs(points, tier, total, category)), {})
        return json.loads(output.getvalue())

    def test_gold_required_example(self):
        result = self.calculate(4250, "Gold", 150)
        self.assertEqual([result[k] for k in ("points_redeemed", "tier_discount_pct", "final_total", "remaining_points")],
                         [4000, 10, 99, 349])

    def test_final_response_preserves_tool_amounts_and_memory(self):
        hook = agent.ToolEvidenceHook()
        result = self.calculate(4250, "Gold", 150)
        hook.after_tool(SimpleNamespace(tool_use={"name": "calculate_loyalty_discount"},
            result={"content": [{"text": json.dumps(result)}]}))
        final = message("assistant", "Wrong model paraphrase: $95 final and $15 tier discount")
        state = SimpleNamespace(messages=[message("user", "Calculate my discount"), final])
        response = SimpleNamespace(message=final)
        hook.finalize_calculation(SimpleNamespace(agent=state, result=response))
        text = agent._text(response.message)
        self.assertIn("10% ($11.00)", text)
        self.assertIn("Final total: $99.00", text)
        self.assertIn("Remaining points: 349", text)
        self.assertNotIn("$95", text)
        client = self.memory()
        agent.MemoryHook("CUST-123", "session", client, "memory").save_support_interaction(
            SimpleNamespace(agent=state, result=response))
        self.assertEqual(client.create_event.call_args.kwargs["messages"][-1], (text, "ASSISTANT"))

    def test_redemption_cap_zero_and_earning_rates(self):
        self.assertEqual(self.calculate(10000, "Silver", 15)["points_redeemed"], 500)
        self.assertEqual(self.calculate(499, "Gold", 10)["points_redeemed"], 0)
        self.assertEqual(self.calculate(10000, "Platinum", 0)["final_total"], 0)
        self.assertEqual(self.calculate(0, "Silver", 10.99, "fresh")["points_earned"], 54)
        self.assertEqual(self.calculate(0, "Silver", 10.99, "device")["points_earned"], 21)

    def test_sandbox_stream_and_cleanup(self):
        result = self.calculate(4250, "Gold", 150)
        with patch.object(agent, "code_session") as factory:
            interpreter = factory.return_value.__enter__.return_value
            interpreter.invoke.return_value = {"stream": iter([{"result": {
                "content": [{"type": "text", "text": json.dumps(result)}], "isError": False}}])}
            self.assertEqual(json.loads(agent.calculate_loyalty_discount(4250, "Gold", 150)), result)
            method, args = interpreter.invoke.call_args.args
            self.assertEqual(method, "executeCode")
            self.assertTrue(args["clearContext"])
            self.assertEqual(args["language"], "python")
            factory.return_value.__exit__.assert_called_once()

    def test_fallback_and_invalid_input(self):
        with patch.object(agent, "code_session", side_effect=RuntimeError()):
            result = json.loads(agent.calculate_loyalty_discount(4250, "Gold", 150))
        self.assertEqual(result["calculation_mode"], "tier_only_fallback")
        self.assertEqual(result["points_redeemed"], 0)
        self.assertEqual(result["remaining_points"], 4250)
        self.assertEqual(result["final_total"], 135)
        for args in [(-1, "Gold", 150), (1, "Invalid", 150), (1, "Gold", float("nan")),
                     (1, "Gold", -1), (True, "Gold", 150)]:
            self.assertIn("error", json.loads(agent.calculate_loyalty_discount(*args)))

    def test_entrypoint_validation_and_missing_config(self):
        for payload in [None, {}, {"prompt": " "}, {"prompt": 1}, {"prompt": "Hi", "customer_id": ""}]:
            self.assertIn("Invalid request", asyncio.run(agent.invoke(payload)))
        with patch.object(agent, "GATEWAY_URL", ""):
            self.assertIn("configuration incomplete", asyncio.run(agent.invoke({"prompt": "Hi"})))

    def test_entrypoint_wiring_success_and_cleanup(self):
        class FakeAgent:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
            async def invoke_async(self, text):
                return SimpleNamespace(message=message("assistant", "Hello!"))
        with patch.multiple(agent, GATEWAY_URL="https://example.invalid/mcp", KB_ID="kb", MEMORY_ID="memory"), \
             patch.object(agent, "MemoryHook") as hook, patch.object(agent, "AgentCoreBrowser") as browser, \
             patch.object(agent, "MCPClient") as gateway, patch.object(agent, "Agent", side_effect=FakeAgent) as model_agent:
            gateway.return_value.__enter__.return_value.list_tools_sync.return_value = ["gateway-tool"]
            result = asyncio.run(agent.invoke({"prompt": "Hi", "customer_id": "CUST-123"}))
            self.assertEqual(result, "Hello!")
            self.assertEqual(hook.call_args.args[0], "CUST-123")
            self.assertTrue(hook.call_args.args[1])
            self.assertIn("gateway-tool", model_agent.call_args.kwargs["tools"])
            browser.return_value.close.assert_called_once()

if __name__ == "__main__":
    unittest.main()
