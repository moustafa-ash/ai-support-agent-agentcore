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
            gateway_tool = SimpleNamespace(tool_name="order-tracker___get_order")
            gateway.return_value.__enter__.return_value.list_tools_sync.return_value = [gateway_tool]
            result = asyncio.run(agent.invoke({"prompt": "Hi", "customer_id": "CUST-123"}))
            self.assertEqual(result, "Hello!")
            self.assertEqual(hook.call_args.args[0], "CUST-123")
            self.assertTrue(hook.call_args.args[1])
            self.assertIn(gateway_tool, model_agent.call_args.kwargs["tools"])
            browser.return_value.close.assert_called_once()

    def test_gateway_setup_failures_are_safe_visible_and_close(self):
        for stage in ("connection", "tool_loading"):
            for error in (TimeoutError, ConnectionError, RuntimeError):
                with self.subTest(stage=stage, error=error.__name__), \
                     patch.multiple(agent, GATEWAY_URL="https://example.invalid/mcp", KB_ID="kb", MEMORY_ID="memory"), \
                     patch.object(agent, "MemoryHook"), patch.object(agent, "AgentCoreBrowser") as browser, \
                     patch.object(agent, "MCPClient") as factory, patch.object(agent, "Agent") as model_agent:
                    gateway = factory.return_value.__enter__.return_value
                    failing = factory.return_value.__enter__ if stage == "connection" else gateway.list_tools_sync
                    failing.side_effect = error("SECRET_ENDPOINT_AND_TOKEN")
                    with self.assertLogs("CSAI_Agent", level="INFO") as logs:
                        result = asyncio.run(agent.invoke({"prompt": "Track my order"}))
                    self.assertEqual(result, agent.GATEWAY_UNAVAILABLE)
                    self.assertIn("GATEWAY_FAILURE", "\n".join(logs.output))
                    self.assertNotIn("SECRET_ENDPOINT_AND_TOKEN", result + "\n".join(logs.output))
                    model_agent.assert_not_called()
                    browser.return_value.close.assert_called_once()
                    if stage == "tool_loading":
                        factory.return_value.__exit__.assert_called_once()

    def test_gateway_discovery_empty_and_success_logs(self):
        with patch.object(agent, "MCPClient") as factory:
            gateway = factory.return_value.__enter__.return_value
            gateway.list_tools_sync.return_value = []
            with self.assertLogs("CSAI_Agent"), self.assertRaises(agent.GatewayUnavailable):
                with agent.gateway_tools():
                    self.fail("Empty tools must not invoke the model")
            tool = SimpleNamespace(tool_name="order-tracker___get_order")
            gateway.list_tools_sync.return_value = [tool]
            with self.assertLogs("CSAI_Agent", level="INFO") as logs:
                with agent.gateway_tools() as tools:
                    self.assertEqual(tools, [tool])
                    self.assertEqual(tool.timeout.total_seconds(), 30)
            self.assertIn("GATEWAY_CONNECTED loaded_tools=1", "\n".join(logs.output))

    def gateway_event(self, name, result, exception=None):
        return SimpleNamespace(tool_use={"name": name, "toolUseId": "test-id"}, result=result, exception=exception)

    def test_gateway_preserves_api_and_unwraps_lambda_results(self):
        for name, data in [("order-tracker___get_order", {"order_id": "ORD-001", "status": "SHIPPED"}),
                           ("refund-processor___initiate_refund", {"refund_id": "REF-TEST", "status": "APPROVED"})]:
            hook = agent.GatewayResponseHook([SimpleNamespace(tool_name=name)])
            raw = data if "get_order" in name else {"statusCode": 200, "body": json.dumps(data)}
            event = self.gateway_event(name, {"status": "success", "content": [{"text": json.dumps(raw)}]})
            with self.assertLogs("CSAI_Agent", level="INFO"):
                hook.after_tool(event)
            self.assertEqual(json.loads(event.result["content"][0]["text"]), data)
            self.assertEqual(event.result["status"], "success")
            self.assertFalse(hook.failures)

    def test_gateway_errors_empty_malformed_and_http_failure(self):
        name = "order-tracker___get_order"
        for raw in [{"status": "error", "content": [{"text": "SECRET"}]},
                    {"status": "success", "isError": True, "content": []},
                    {"status": "success", "content": []},
                    {"status": "success", "content": [{"text": " "}]},
                    {"status": "success", "content": [{"text": "{}"}]},
                    {"status": "success", "content": [{"text": "null"}]},
                    {"status": "success", "content": [{"text": "malformed SECRET"}]},
                    {"status": "success", "structuredContent": {"statusCode": 500, "body": "SECRET"}},
                    {"status": "success", "structuredContent": {"error": "SECRET"}}]:
            with self.subTest(raw=raw):
                hook = agent.GatewayResponseHook([SimpleNamespace(tool_name=name)])
                event = self.gateway_event(name, raw)
                with self.assertLogs("CSAI_Agent"):
                    hook.after_tool(event)
                self.assertEqual(event.result["status"], "error")
                self.assertIn("try again", event.result["content"][0]["text"])
                self.assertNotIn("SECRET", json.dumps(event.result))
                final = message("assistant", "Invented success")
                state = SimpleNamespace(messages=[message("user", "Track my order"), final])
                hook.finalize_failure(SimpleNamespace(agent=state, result=SimpleNamespace(message=final)))
                self.assertEqual(agent._text(final), agent.GATEWAY_UNAVAILABLE)

    def test_refund_exception_reports_uncertain_outcome_without_retry(self):
        name = "refund-processor___initiate_refund"
        hook = agent.GatewayResponseHook([SimpleNamespace(tool_name=name)])
        event = self.gateway_event(name, {}, TimeoutError("SECRET"))
        with self.assertLogs("CSAI_Agent"):
            hook.after_tool(event)
        self.assertIn("before retrying", agent._text(event.result))
        self.assertIn("duplicate refund", agent._text(event.result))
        self.assertNotIn("SECRET", agent._text(event.result))
        self.assertFalse(hasattr(event, "retry"))

    def test_gateway_failure_saved_as_customer_response(self):
        name = "order-tracker___get_order"
        hook = agent.GatewayResponseHook([SimpleNamespace(tool_name=name)])
        hook.failures[name] = agent.GATEWAY_UNAVAILABLE
        final = message("assistant", "Invented success")
        state = SimpleNamespace(messages=[message("user", "Track order"), final])
        event = SimpleNamespace(agent=state, result=SimpleNamespace(message=final))
        hook.finalize_failure(event)
        client = self.memory()
        agent.MemoryHook("CUST-123", "session", client, "memory").save_support_interaction(event)
        self.assertEqual(client.create_event.call_args.kwargs["messages"][-1],
                         (agent.GATEWAY_UNAVAILABLE, "ASSISTANT"))

    def test_gateway_error_takes_precedence_over_discount_rendering(self):
        guard = agent.GatewayResponseHook([])
        guard.failures["refund"] = "Refund outcome unconfirmed. Check status before retrying."
        evidence = agent.ToolEvidenceHook(guard)
        evidence.discount = self.calculate(4250, "Gold", 150)
        final = message("assistant", "Incorrect success claim")
        event = SimpleNamespace(agent=SimpleNamespace(messages=[final]), result=SimpleNamespace(message=final))
        guard.finalize_failure(event)
        evidence.finalize_calculation(event)
        self.assertIn("unconfirmed", agent._text(final))

    def test_real_sdk_hook_mutation_and_evidence_order(self):
        name = "refund-processor___initiate_refund"
        guard = agent.GatewayResponseHook([SimpleNamespace(tool_name=name)])
        evidence = agent.ToolEvidenceHook(guard)
        registry = agent.HookRegistry()
        evidence.register_hooks(registry)
        guard.register_hooks(registry)
        event = agent.AfterToolCallEvent(agent=SimpleNamespace(), selected_tool=None,
            tool_use={"name": name, "toolUseId": "sdk-id", "input": {}}, invocation_state={},
            result={"status": "success", "content": [{"text": json.dumps({"statusCode": 200,
                    "body": json.dumps({"refund_id": "REF-TEST", "status": "APPROVED"})})}]})
        with patch.dict(os.environ, PROJECT_EVIDENCE="true"), self.assertLogs("CSAI_Agent", level="INFO") as logs:
            registry.invoke_callbacks(event)
        self.assertEqual(json.loads(event.result["content"][0]["text"])["refund_id"], "REF-TEST")
        trace = "\n".join(logs.output)
        self.assertIn("GATEWAY_TOOL_SUCCESS", trace)
        self.assertIn("TOOL_EVIDENCE", trace)
        self.assertNotIn("statusCode", trace)

if __name__ == "__main__":
    unittest.main()
