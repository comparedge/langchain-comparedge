"""ComparEdge SaaS Data Loader for LangChain."""

from typing import Iterator, List, Optional

import requests


class Document:
    """Minimal Document class for standalone use (mirrors langchain_core.documents.Document)."""

    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata

    def __repr__(self) -> str:
        preview = self.page_content[:80].replace("\n", " ")
        return f"Document(name={self.metadata.get('name', '')!r}, preview={preview!r})"


class ComparEdgeLoader:
    """Load SaaS product data from the ComparEdge API.

    ComparEdge tracks pricing, ratings, and features for 331 software products
    across 28 categories. No API key required.

    API docs: https://comparedge-api.up.railway.app/docs

    Examples:
        Load all CRM products::

            loader = ComparEdgeLoader(category="crm", include_pricing=True)
            docs = loader.load()

        Load everything::

            loader = ComparEdgeLoader()
            docs = loader.load()
    """

    BASE_URL = "https://comparedge-api.up.railway.app/api/v1"

    def __init__(
        self,
        category: Optional[str] = None,
        include_pricing: bool = True,
        include_features: bool = False,
    ):
        """Initialize the ComparEdge loader.

        Args:
            category: Filter by category slug (e.g., "crm", "llm", "project-management").
                      If None, loads all products.
            include_pricing: Include pricing plan details in document text + starting_price
                             in metadata.
            include_features: Append feature list to document text (capped at 20 per product).
        """
        self.category = category
        self.include_pricing = include_pricing
        self.include_features = include_features

    def lazy_load(self) -> Iterator[Document]:
        """Lazily yield SaaS product documents from the ComparEdge API.

        Paginates automatically through all results using offset/limit.
        """
        params: dict = {"limit": 50, "offset": 0}
        if self.category:
            params["category"] = self.category

        url = f"{self.BASE_URL}/products"

        while True:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            products = data.get("products", [])
            if not products:
                break

            for product in products:
                yield self._product_to_document(product)

            total = data.get("total", 0)
            params["offset"] += len(products)
            if params["offset"] >= total:
                break

    def load(self) -> List[Document]:
        """Load all documents and return as a list."""
        return list(self.lazy_load())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _product_to_document(self, product: dict) -> Document:
        content_parts: List[str] = []

        content_parts.append(f"# {product.get('name', 'Unknown')}")
        content_parts.append(f"Category: {product.get('category', 'N/A')}")

        description = product.get("description") or product.get("shortDescription")
        if description:
            content_parts.append(f"\n{description}")

        pricing = product.get("pricing") or {}
        plans = pricing.get("plans") or []

        if self.include_pricing and plans:
            content_parts.append("\n## Pricing")
            for plan in plans:
                name = plan.get("name", "Unknown")
                price = plan.get("price")
                period = plan.get("period", "")
                if not price:
                    content_parts.append(f"- {name}: Free")
                else:
                    content_parts.append(f"- {name}: ${price}/{period}")

        if self.include_features:
            features = product.get("features") or product.get("normalizedFeatures") or []
            if features:
                content_parts.append("\n## Features")
                for feat in features[:20]:
                    if isinstance(feat, str):
                        content_parts.append(f"- {feat}")
                    elif isinstance(feat, dict):
                        label = feat.get("name") or feat.get("feature") or feat.get("label", "")
                        if label:
                            content_parts.append(f"- {label}")

        ratings = product.get("rating") or product.get("ratings") or {}
        metadata = {
            "source": f"https://comparedge.com/tools/{product.get('slug', '')}",
            "name": product.get("name", ""),
            "slug": product.get("slug", ""),
            "category": product.get("category", ""),
            "g2_rating": ratings.get("g2") if isinstance(ratings, dict) else None,
            "has_free_tier": bool(pricing.get("free", False)),
            "website": product.get("url") or product.get("website", ""),
        }

        if self.include_pricing and plans:
            paid = [p["price"] for p in plans if isinstance(p.get("price"), (int, float)) and p["price"] > 0]
            if paid:
                metadata["starting_price"] = min(paid)

        return Document(
            page_content="\n".join(content_parts),
            metadata=metadata,
        )
