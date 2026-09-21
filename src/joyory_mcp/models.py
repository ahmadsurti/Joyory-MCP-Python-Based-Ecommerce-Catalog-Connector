"""Pydantic models for normalized Joyory product data."""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, computed_field


class ProductSummary(BaseModel):
    """Compact product record returned by search_products."""
    id: str
    name: str
    brand: str | None = None
    category: str | None = None          # leaf category name
    category_slug: str | None = None     # e.g. "skin-sun-care-sunscreen"
    size: str | None = None              # e.g. "200 ml", "60 g"
    price: float | None = None
    mrp: float | None = None             # original price before discount
    currency: str = "INR"
    price_per_100ml: float | None = None # only set when size is parseable ml/g
    short_description: str | None = None
    tags: list[str] = Field(default_factory=list)  # e.g. ["fragrance-free", "oily-skin"]
    rating: float | None = None          # null means no reviews yet (NOT a bad rating)
    rating_count: int | None = None
    in_stock: bool | None = None
    match: Literal["exact", "partial", "weak"] = "exact"  # search relevance signal
    url: str | None = None
    image_url: str | None = None         # omitted when include_images=False


class VariantInfo(BaseModel):
    """A single product variant (size, shade, flavor, etc.)."""
    id: str | None = None
    name: str | None = None              # shade name or size label
    size: str | None = None
    shade: str | None = None
    hex_color: str | None = None
    price: float | None = None
    mrp: float | None = None
    in_stock: bool | None = None
    sku: str | None = None
    image_url: str | None = None


class ProductAttributes(BaseModel):
    """Structured skincare/cosmetic attributes extracted from a product."""
    skin_types: list[str] = Field(default_factory=list)   # ["oily", "combination"]
    concerns: list[str] = Field(default_factory=list)     # extracted from description/tags
    formulation: str | None = None                        # Liquid, Gel, Cream, etc.
    spf: str | None = None                                # "SPF 50 PA++++"
    fragrance_free: bool | None = None                    # null = unknown (incomplete INCI list)
    finish: str | None = None                             # matte, glossy, dewy
    key_ingredients: list[str] = Field(default_factory=list)  # actives, not fillers
    inci_complete: bool = False                           # True = full INCI list; False = marketing text only


class ProductDetail(BaseModel):
    """Full product record returned by get_product_details."""
    id: str
    name: str
    brand: str | None = None
    category: str | None = None
    category_slug: str | None = None
    size: str | None = None
    price: float | None = None
    mrp: float | None = None
    currency: str = "INR"
    short_description: str | None = None
    description: str | None = None
    description_warning: str | None = None  # set when description looks like leaked AI/review text
    ingredients: list[str] = Field(default_factory=list)
    how_to_use: str | None = None
    attributes: ProductAttributes = Field(default_factory=ProductAttributes)
    rating: float | None = None
    rating_count: int | None = None
    in_stock: bool | None = None
    images: list[str] = Field(default_factory=list)
    url: str | None = None
    tags: list[str] = Field(default_factory=list)
    variants: list[VariantInfo] = Field(default_factory=list)

    @computed_field
    @property
    def variant_information(self) -> list[VariantInfo]:
        """Backward compatibility alias for variants."""
        return self.variants


class SearchResponse(BaseModel):
    """Wrapper for search_products response."""
    query: str
    total_matches: int
    has_more: bool = False
    count: int                           # items in this page
    offset: int = 0
    results: list[ProductSummary]
    source: str = "joyory"
    hint: str | None = None             # e.g. "no matches; try category skin-moisturizer"
