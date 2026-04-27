"""Tests for the ComparEdge LangChain document loader."""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Minimal stubs so this file is importable without langchain_core installed
# ---------------------------------------------------------------------------

def _ensure_stubs():
    """Insert minimal langchain_core stubs into sys.modules if not present."""
    if "langchain_core" not in sys.modules:
        core = types.ModuleType("langchain_core")
        loaders_mod = types.ModuleType("langchain_core.document_loaders")
        docs_mod = types.ModuleType("langchain_core.documents")

        class BaseLoader:  # noqa: D101
            def load(self):
                return list(self.lazy_load())

        class Document:  # noqa: D101
            def __init__(self, page_content: str, metadata: dict):
                self.page_content = page_content
                self.metadata = metadata

        loaders_mod.BaseLoader = BaseLoader
        docs_mod.Document = Document

        sys.modules["langchain_core"] = core
        sys.modules["langchain_core.document_loaders"] = loaders_mod
        sys.modules["langchain_core.documents"] = docs_mod


_ensure_stubs()

import importlib
import os

# Allow running from repo root or from langchain_pr/
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from comparedge import ComparEdgeLoader  # noqa: E402  (after path fix)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_PRODUCT = {
    "slug": "notion",
    "name": "Notion",
    "url": "https://notion.so",
    "category": "project-management",
    "description": "All-in-one workspace for notes, docs, and projects.",
    "pricing": {
        "free": True,
        "plans": [
            {"name": "Free", "price": 0, "period": "user/mo"},
            {"name": "Plus", "price": 12, "period": "user/mo"},
            {"name": "Business", "price": 18, "period": "user/mo"},
            {"name": "Enterprise", "price": None, "period": "user/mo"},
        ],
    },
    "features": ["Docs & Pages", "Databases", "Kanban Boards"],
    "normalizedFeatures": [],
    "rating": {"g2": 4.7, "capterra": 4.7},
    "founded": 2016,
    "hq": "San Francisco, CA",
}

MOCK_API_RESPONSE = {
    "total": 2,
    "limit": 50,
    "offset": 0,
    "products": [
        MOCK_PRODUCT,
        {
            "slug": "asana",
            "name": "Asana",
            "url": "https://asana.com",
            "category": "project-management",
            "description": "Work management platform.",
            "pricing": {
                "free": True,
                "plans": [
                    {"name": "Personal", "price": 0, "period": "user/mo"},
                    {"name": "Starter", "price": 10.99, "period": "user/mo"},
                ],
            },
            "features": ["Task Management", "Timeline"],
            "normalizedFeatures": [],
            "rating": {"g2": 4.3},
        },
    ],
    "_links": {},
}


def _mock_get(response_data, status_code=200):
    """Return a mock requests.get that yields response_data once then empty."""
    call_count = 0

    def _get(url, params=None, timeout=None):
        nonlocal call_count
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        if call_count == 0:
            mock_resp.json.return_value = response_data
        else:
            # Subsequent pages → empty products list to terminate pagination
            mock_resp.json.return_value = {"total": response_data["total"], "limit": 50, "offset": 50, "products": []}
        call_count += 1
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    return _get


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLoaderInit(unittest.TestCase):
    def test_defaults(self):
        loader = ComparEdgeLoader()
        self.assertIsNone(loader.category)
        self.assertTrue(loader.include_pricing)
        self.assertFalse(loader.include_features)

    def test_custom_params(self):
        loader = ComparEdgeLoader(category="crm", include_pricing=False, include_features=True)
        self.assertEqual(loader.category, "crm")
        self.assertFalse(loader.include_pricing)
        self.assertTrue(loader.include_features)


class TestLoadAll(unittest.TestCase):
    @patch("requests.get", side_effect=_mock_get(MOCK_API_RESPONSE))
    def test_returns_documents(self, _mock):
        loader = ComparEdgeLoader()
        docs = loader.load()
        self.assertEqual(len(docs), 2)

    @patch("requests.get", side_effect=_mock_get(MOCK_API_RESPONSE))
    def test_no_category_param_sent(self, mock_get):
        loader = ComparEdgeLoader()
        loader.load()
        _, kwargs = mock_get.call_args
        self.assertNotIn("category", kwargs.get("params", {}))

    @patch("requests.get", side_effect=_mock_get(MOCK_API_RESPONSE))
    def test_lazy_load_yields(self, _mock):
        loader = ComparEdgeLoader()
        gen = loader.lazy_load()
        first = next(gen)
        self.assertEqual(first.metadata["name"], "Notion")


class TestLoadCategory(unittest.TestCase):
    @patch("requests.get", side_effect=_mock_get(MOCK_API_RESPONSE))
    def test_category_param_forwarded(self, mock_get):
        loader = ComparEdgeLoader(category="project-management")
        loader.load()
        _, kwargs = mock_get.call_args_list[0]
        self.assertEqual(kwargs["params"].get("category"), "project-management")

    @patch("requests.get", side_effect=_mock_get(MOCK_API_RESPONSE))
    def test_category_documents_returned(self, _mock):
        loader = ComparEdgeLoader(category="project-management")
        docs = loader.load()
        self.assertGreater(len(docs), 0)
        for doc in docs:
            self.assertEqual(doc.metadata["category"], "project-management")


class TestDocumentSchema(unittest.TestCase):
    def _load_one(self, **kwargs):
        single_response = {**MOCK_API_RESPONSE, "total": 1, "products": [MOCK_PRODUCT]}
        with patch("requests.get", side_effect=_mock_get(single_response)):
            loader = ComparEdgeLoader(**kwargs)
            return loader.load()[0]

    def test_required_metadata_keys(self):
        doc = self._load_one()
        for key in ("source", "name", "slug", "category", "g2_rating", "has_free_tier", "website"):
            self.assertIn(key, doc.metadata, f"Missing metadata key: {key}")

    def test_source_url_format(self):
        doc = self._load_one()
        self.assertTrue(doc.metadata["source"].startswith("https://comparedge.com/tools/"))

    def test_g2_rating_value(self):
        doc = self._load_one()
        self.assertAlmostEqual(doc.metadata["g2_rating"], 4.7)

    def test_has_free_tier(self):
        doc = self._load_one()
        self.assertTrue(doc.metadata["has_free_tier"])

    def test_starting_price_with_pricing(self):
        doc = self._load_one(include_pricing=True)
        self.assertIn("starting_price", doc.metadata)
        self.assertEqual(doc.metadata["starting_price"], 12)

    def test_no_starting_price_when_pricing_disabled(self):
        doc = self._load_one(include_pricing=False)
        self.assertNotIn("starting_price", doc.metadata)

    def test_page_content_has_name(self):
        doc = self._load_one()
        self.assertIn("Notion", doc.page_content)

    def test_page_content_has_description(self):
        doc = self._load_one()
        self.assertIn("workspace", doc.page_content)

    def test_pricing_section_in_content(self):
        doc = self._load_one(include_pricing=True)
        self.assertIn("## Pricing", doc.page_content)
        self.assertIn("Plus", doc.page_content)

    def test_no_pricing_section_when_disabled(self):
        doc = self._load_one(include_pricing=False)
        self.assertNotIn("## Pricing", doc.page_content)

    def test_features_section_in_content(self):
        doc = self._load_one(include_features=True)
        self.assertIn("## Features", doc.page_content)
        self.assertIn("Docs & Pages", doc.page_content)

    def test_features_capped_at_20(self):
        # Product with 25 features — only 20 should appear
        product = {
            **MOCK_PRODUCT,
            "features": [f"Feature {i}" for i in range(25)],
        }
        response = {**MOCK_API_RESPONSE, "total": 1, "products": [product]}
        with patch("requests.get", side_effect=_mock_get(response)):
            loader = ComparEdgeLoader(include_features=True)
            doc = loader.load()[0]
        feature_lines = [l for l in doc.page_content.splitlines() if l.startswith("- Feature")]
        self.assertEqual(len(feature_lines), 20)

    def test_null_enterprise_price_shown_as_free(self):
        doc = self._load_one(include_pricing=True)
        self.assertIn("Enterprise: Free", doc.page_content)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    # Pretty-print results
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
