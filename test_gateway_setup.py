import ast
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch


class NotebookGatewaySetupTests(unittest.TestCase):
    def test_chat_credentials_in_each_notebook(self):
        setup_cells = []
        for path in Path(__file__).parent.glob("module-*/*.ipynb"):
            notebook = json.loads(path.read_text())
            for cell in notebook["cells"]:
                source = "".join(cell.get("source", []))
                if (
                    cell["cell_type"] == "code"
                    and '_set_env("OPENAI_API_KEY")' in source
                ):
                    setup_cells.append((path, source))
        self.assertGreater(len(setup_cells), 15)
        for path, source in setup_cells:
            setup = ast.parse(source)
            setup.body = [
                node for node in setup.body if isinstance(node, (ast.If, ast.Expr))
            ]
            for flag in (
                "",
                "false",
                "0",
                "no",
                "FALSE",
                "true",
                "1",
                "yes",
                "https://eu.gateway.smith.langchain.com",
            ):
                for gateway_key in ("", "gateway-key"):
                    for langsmith_key in ("", "langsmith-key"):
                        with self.subTest(
                            notebook=path.name,
                            flag=flag,
                            gateway_key=gateway_key,
                            langsmith_key=langsmith_key,
                        ):
                            environ = {
                                "LANGSMITH_GATEWAY": flag,
                                "LANGSMITH_GATEWAY_API_KEY": gateway_key,
                                "LANGSMITH_API_KEY": langsmith_key,
                            }
                            prompts = []

                            def set_env(key, prompts=prompts):
                                if not os.environ.get(key):
                                    prompts.append(key)

                            with patch.dict(os.environ, environ, clear=True):
                                exec(
                                    compile(setup, str(path), "exec"),
                                    {"os": os, "_set_env": set_env},
                                )
                            enabled = flag.lower() not in ("", "false", "0", "no")
                            expected = (
                                (
                                    []
                                    if gateway_key or langsmith_key
                                    else ["LANGSMITH_API_KEY"]
                                )
                                if enabled
                                else ["OPENAI_API_KEY"]
                            )
                            self.assertEqual(prompts, expected)


if __name__ == "__main__":
    unittest.main()
