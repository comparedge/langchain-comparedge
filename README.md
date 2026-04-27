# ComparEdge Data Loader for LangChain

Pulls SaaS product data from the ComparEdge API into LangChain Documents. Real SaaS pricing — plans, features, ratings. No API key.

## Quick start

```python
from comparedge_loader import ComparEdgeLoader

# Load all LLM products
loader = ComparEdgeLoader(category="llm", include_pricing=True)
docs = loader.load()

# Each doc: product name, description, pricing plans
for doc in docs[:3]:
    print(doc.metadata["name"], doc.metadata.get("starting_price"))
```

## Parameters

| Param | Type | Default | What it does |
|-------|------|---------|-------------|
| `category` | str or None | None | Filter by slug: `"crm"`, `"llm"`, `"project-management"`, etc. `None` = all products |
| `include_pricing` | bool | True | Add pricing plans to document text + `starting_price` to metadata |
| `include_features` | bool | False | Append feature list to document text (capped at 20 per product) |

### Available category slugs

`accounting`, `ai-agents`, `analytics`, `bi-tools`, `cms`, `crm`, `customer-support`,
`data-pipeline`, `design`, `devops`, `email-marketing`, `erp`, `helpdesk`, `hr`,
`llm`, `marketing-automation`, `monitoring`, `project-management`, `sales`,
`security`, `seo`, `social-media`, `storage`, `video-conferencing`, `and more`

Full list: `GET https://comparedge-api.up.railway.app/api/v1/categories`

## Document schema

**page_content**: Markdown-formatted text with product name, category, description, optional pricing table, optional features list.

**metadata**:

| Key | Type | Description |
|-----|------|-------------|
| `source` | str | Canonical URL on comparedge.com |
| `name` | str | Product display name |
| `slug` | str | URL-safe identifier |
| `category` | str | Category slug |
| `g2_rating` | float or null | G2 crowd rating |
| `has_free_tier` | bool | Product has a free plan |
| `starting_price` | float | Lowest paid plan price (when `include_pricing=True`) |
| `website` | str | Vendor homepage |

## Sample document

```
# Notion
Category: project-management

All-in-one workspace for notes, docs, and projects.

## Pricing
- Free: Free
- Plus: $12/user/mo
- Business: $18/user/mo
- Enterprise: Free
```

## Use cases

- RAG pipeline for software recommendation chatbots
- Automated vendor evaluation reports
- Price monitoring agents
- SaaS stack analysis
- Competitive intelligence

## Pagination

The loader paginates automatically. All matching products are streamed via `lazy_load()` without loading the full dataset into memory at once.

```python
# Memory-efficient streaming
loader = ComparEdgeLoader()
for doc in loader.lazy_load():
    index(doc)
```

## API

Base URL: `https://comparedge-api.up.railway.app/api/v1`

No auth required. Be reasonable with request rate.

Docs: https://comparedge-api.up.railway.app/docs

## Integration with LangChain (PR target)

This loader targets `langchain_community.document_loaders`. The PR-ready file is at `langchain_pr/comparedge.py`.

Expected import after merge:

```python
from langchain_community.document_loaders import ComparEdgeLoader
```

## Testing

```bash
# Unit tests (mocked, no network)
python langchain_pr/test_comparedge.py

# Live test against the API
python example.py
```
