"""Example: Build a simple SaaS recommendation agent with ComparEdge data."""

from comparedge_loader import ComparEdgeLoader

# ---------------------------------------------------------------------------
# 1. Load CRM products with pricing and features
# ---------------------------------------------------------------------------

loader = ComparEdgeLoader(category="crm", include_pricing=True, include_features=True)
docs = loader.load()

print(f"Loaded {len(docs)} CRM products\n")

# ---------------------------------------------------------------------------
# 2. Show top free CRMs by G2 rating
# ---------------------------------------------------------------------------

free_crms = [d for d in docs if d.metadata.get("has_free_tier")]
free_crms.sort(key=lambda d: d.metadata.get("g2_rating") or 0, reverse=True)

print("Top free CRMs by G2 rating:")
for doc in free_crms[:5]:
    rating = doc.metadata.get("g2_rating")
    stars = f"{rating} ★" if rating else "no rating"
    print(f"  {doc.metadata['name']}: {stars} — {doc.metadata['source']}")

# ---------------------------------------------------------------------------
# 3. Price range breakdown
# ---------------------------------------------------------------------------

priced = [d for d in docs if d.metadata.get("starting_price")]
if priced:
    prices = [d.metadata["starting_price"] for d in priced]
    print(f"\nPricing range across {len(priced)} paid CRM products:")
    print(f"  Cheapest: ${min(prices)}/mo  |  Most expensive: ${max(prices)}/mo")
    print(f"  Average:  ${sum(prices)/len(prices):.2f}/mo")

# ---------------------------------------------------------------------------
# 4. Preview first document
# ---------------------------------------------------------------------------

print("\n--- First document preview ---")
print(docs[0].page_content[:400])
print("...")
print("\nMetadata:", docs[0].metadata)
