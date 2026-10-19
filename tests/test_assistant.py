import json
import os
import ssl
import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from openai import APIConnectionError, APITimeoutError, APIStatusError
from langchain_core.messages import AIMessageChunk, ToolMessage

from agent import langchain_assistant as assistant


class ModelClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_clients_verify_tls_and_are_closed(self):
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key", "OPENAI_BASE_URL": "https://example.invalid/v1",
        }), patch("openai.DefaultHttpxClient") as sync_factory, patch(
            "openai.DefaultAsyncHttpxClient"
        ) as async_factory, patch("langchain_openai.ChatOpenAI") as model_factory, patch.object(
            assistant, "model_http_client", None
        ), patch.object(assistant, "model_async_http_client", None), patch.object(assistant, "agent", None):
            async_factory.return_value.aclose = AsyncMock()
            assistant.create_chat_model()
            context = sync_factory.call_args.kwargs["verify"]
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)
            self.assertIs(context, async_factory.call_args.kwargs["verify"])
            self.assertIs(model_factory.call_args.kwargs["http_client"], sync_factory.return_value)
            self.assertIs(model_factory.call_args.kwargs["http_async_client"], async_factory.return_value)
            self.assertEqual(model_factory.call_args.kwargs["max_retries"], 1)
            self.assertEqual(model_factory.call_args.kwargs["timeout"], 30)
            assistant.create_chat_model()
            self.assertEqual(sync_factory.call_count, 1)
            self.assertEqual(async_factory.call_count, 1)
            await assistant.close_model_clients()
            sync_factory.return_value.close.assert_called_once()
            async_factory.return_value.aclose.assert_awaited_once()
            self.assertIsNone(assistant.model_http_client)
            self.assertIsNone(assistant.model_async_http_client)

    async def test_missing_configuration(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "OPENAI_BASE_URL": ""}):
            with self.assertRaises(assistant.AssistantConfigurationError):
                assistant.create_chat_model()


class MenuFallbackTests(unittest.TestCase):
    def menu_connection(self, rows):
        engine = MagicMock()
        connection = engine.connect.return_value.__enter__.return_value
        connection.execute.return_value.mappings.return_value.all.return_value = rows
        return engine, connection

    def test_menu_query_preserves_fields_and_filters_available(self):
        engine, conn = self.menu_connection([
            {"id": 1, "dish_name": "红烧肉", "price": Decimal("48.00"), "spice_level": 0},
        ])
        with patch.object(assistant, "mysql_connection", return_value=engine):
            result = assistant.load_available_menu()
        self.assertEqual(result["source"], "mysql")
        self.assertEqual(result["menu_items"][0]["price"], "48.00")
        self.assertEqual(result["menu_items"][0]["spice_level"], 0)
        self.assertIn("WHERE is_available = 1", str(conn.execute.call_args.args[0]))
        json.dumps(result)

    def test_empty_menu(self):
        engine, _ = self.menu_connection([])
        with patch.object(assistant, "mysql_connection", return_value=engine):
            result = assistant.load_available_menu()
        self.assertEqual(result["menu_items"], [])
        self.assertIn("暂无", result["message"])

    def test_database_failure_does_not_expose_credentials(self):
        with patch.object(assistant, "mysql_connection", side_effect=RuntimeError("secret-password")), self.assertLogs(assistant.logger, level="ERROR"):
            result = assistant.load_available_menu()
        self.assertIn("error", result)
        self.assertNotIn("secret-password", json.dumps(result))

    def test_unconfigured_vector_service_skips_embedding_loading(self):
        with patch.dict(os.environ, {"MILVUS_URI": "https://{cluster-id}.example.com"}), patch.object(
            assistant, "get_embeddings"
        ) as embeddings, patch.object(assistant, "load_available_menu", return_value={"source": "mysql"}) as fallback:
            result = assistant.user_flavor_search.invoke({"user_query": "不辣的菜"})
        embeddings.assert_not_called()
        fallback.assert_called_once()
        self.assertEqual(result["source"], "mysql")

    def test_vector_failure_uses_database(self):
        with patch.dict(os.environ, {"MILVUS_URI": "http://localhost:19530"}), patch(
            "pathlib.Path.is_dir", return_value=True
        ), patch.object(assistant, "get_embeddings", side_effect=RuntimeError("unavailable")), patch.object(
            assistant, "load_available_menu", return_value={"source": "mysql"}
        ) as fallback, self.assertLogs(assistant.logger, level="WARNING"):
            result = assistant.user_flavor_search.invoke({"user_query": "不辣的菜"})
        fallback.assert_called_once()
        self.assertEqual(result["source"], "mysql")

    def test_vector_result_is_labelled(self):
        client = MagicMock()
        client.search.return_value = [[{"entity": {"text": "红烧肉 48 元"}}]]
        with patch.dict(os.environ, {"MILVUS_URI": "http://localhost:19530"}), patch(
            "pathlib.Path.is_dir", return_value=True
        ), patch.object(assistant, "get_embeddings"), patch.object(
            assistant, "get_milvus_client", return_value=client
        ), patch.object(assistant, "load_available_menu") as fallback:
            result = assistant.user_flavor_search.invoke({"user_query": "不辣"})
        self.assertEqual(result, {"source": "milvus", "results": ["红烧肉 48 元"]})
        fallback.assert_not_called()

    def test_empty_vector_result_uses_database(self):
        client = MagicMock()
        client.search.return_value = [[]]
        with patch.dict(os.environ, {"MILVUS_URI": "http://localhost:19530"}), patch(
            "pathlib.Path.is_dir", return_value=True
        ), patch.object(assistant, "get_embeddings"), patch.object(
            assistant, "get_milvus_client", return_value=client
        ), patch.object(assistant, "load_available_menu", return_value={"source": "mysql"}):
            result = assistant.user_flavor_search.invoke({"user_query": "不辣"})
        self.assertEqual(result["source"], "mysql")


class StreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_assistant_text_is_streamed(self):
        async def stream(*args, **kwargs):
            yield (ToolMessage(content="internal tool data", tool_call_id="t1"), {})
            yield (AIMessageChunk(content="你好"), {})
            yield (AIMessageChunk(content=[{"type": "text", "text": "欢迎光临"}]), {})
        model = MagicMock()
        model.astream = stream
        with patch.object(assistant, "create_agent", new=AsyncMock(return_value=model)):
            events = [json.loads(line.removeprefix("data: ")) async for line in assistant.assistant_query("你好")]
        self.assertEqual([event["content"] for event in events], ["你好", "欢迎光临"])
        self.assertTrue(all(event["type"] == "token" for event in events))

    async def test_configuration_error_is_actionable(self):
        with patch.object(assistant, "create_agent", new=AsyncMock(side_effect=assistant.AssistantConfigurationError("secret"))), self.assertLogs(assistant.logger, level="ERROR"):
            events = [json.loads(line.removeprefix("data: ")) async for line in assistant.assistant_query("你好")]
        self.assertEqual(events[0]["type"], "error")
        self.assertIn("OPENAI_API_KEY", events[0]["error"])
        self.assertNotIn("secret", str(events))

    async def test_mid_stream_error_is_reported_without_raw_exception(self):
        async def stream(*args, **kwargs):
            yield (AIMessageChunk(content="你好"), {})
            raise RuntimeError("secret upstream response")
        model = MagicMock()
        model.astream = stream
        with patch.object(assistant, "create_agent", new=AsyncMock(return_value=model)), self.assertLogs(assistant.logger, level="ERROR"):
            events = [json.loads(line.removeprefix("data: ")) async for line in assistant.assistant_query("你好")]
        self.assertEqual([event["type"] for event in events], ["token", "error"])
        self.assertNotIn("secret", str(events))

    async def test_timeout_and_connection_errors_are_specific(self):
        request = MagicMock()
        self.assertIn("超时", assistant.assistant_error_message(APITimeoutError(request=request)))
        self.assertIn("无法连接", assistant.assistant_error_message(APIConnectionError(request=request)))

    async def test_status_errors_never_return_upstream_body(self):
        for status, expected in ((401, "鉴权"), (403, "权限"), (429, "额度"), (404, "OPENAI_MODEL"), (500, "异常")):
            response = MagicMock(status_code=status)
            error = APIStatusError("secret", response=response, body={"api_key": "secret"})
            message = assistant.assistant_error_message(error)
            self.assertIn(expected, message)
            self.assertNotIn("secret", message)


if __name__ == "__main__":
    unittest.main()
