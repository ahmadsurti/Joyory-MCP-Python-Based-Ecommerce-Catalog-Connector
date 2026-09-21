"""
Normalization layer — converts raw Joyory JSON into clean Pydantic models.
Only this file + adapters know about Joyory's internal schema.
"""

from __future__ import annotations
import re
from typing import Any
from joyory_mcp.models import ProductSummary, ProductDetail, VariantInfo, ProductAttributes
from joyory_mcp import config as cfg


# ── Brand slug normalisation ──────────────────────────────────────────────────

def _to_brand_slug(brand: str) -> str:
    """Normalise any brand input to Joyory slug format.
    'DOT & KEY' -> 'dot-key', "Dr Sheth's" -> 'dr-sheth-s'
    """
    s = brand.lower().strip()
    s = re.sub(r"['\u2019]", "-", s)    # apostrophes
    s = re.sub(r"[^a-z0-9]+", "-", s)  # everything else non-alnum
    return s.strip("-")


# ── Scalar helpers ────────────────────────────────────────────────────────────

def _first(*values: Any) -> Any:
    for v in values:
        if v is not None and v != "" and v != []:
            return v
    return None


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "").replace("₹", "").strip())
    except (ValueError, TypeError):
        return None


def _to_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(str(v).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _to_bool_stock(v: Any) -> bool | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v > 0
    s = str(v).lower()
    if s in ("true", "1", "yes", "in stock", "instock", "available"):
        return True
    if s in ("false", "0", "no", "out of stock", "outofstock", "unavailable"):
        return False
    return None


def _full_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("http"):
        return path
    return cfg.BASE_URL + ("" if path.startswith("/") else "/") + path


def _image_url(raw: Any) -> str | None:
    if not raw:
        return None
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    if isinstance(raw, dict):
        raw = _first(raw.get("url"), raw.get("src"), raw.get("large"), raw.get("medium"))
    return _full_url(raw) if raw else None


# ── Field extractors ──────────────────────────────────────────────────────────

def _extract_id(raw: dict) -> str:
    candidate = _first(
        raw.get("_id"), raw.get("id"), raw.get("productId"), raw.get("product_id"),
        raw.get("sku"), raw.get("slug"), raw.get("handle"), raw.get("code"),
    )
    if candidate is not None:
        return str(candidate)
    slugs = raw.get("slugs")
    if isinstance(slugs, list) and slugs:
        return f"slug_{slugs[0]}"
    url = raw.get("url") or raw.get("productUrl") or raw.get("permalink") or ""
    if url:
        slug = url.rstrip("/").split("/")[-1]
        if slug:
            return f"slug_{slug}"
    return "unknown"


def _extract_name(raw: dict) -> str:
    return str(_first(
        raw.get("name"), raw.get("productName"), raw.get("title"),
        raw.get("displayName"), raw.get("product_name"),
    ) or "Unknown Product")


def _extract_brand(raw: dict) -> str | None:
    v = _first(raw.get("brand"), raw.get("brandName"), raw.get("brand_name"), raw.get("manufacturer"))
    if isinstance(v, dict):
        v = v.get("name") or v.get("brandName") or v.get("slug")
    return str(v) if v else None


def _extract_price(raw: dict) -> float | None:
    return _to_float(_first(
        raw.get("discountedPrice"), raw.get("price"), raw.get("salePrice"),
        raw.get("sale_price"), raw.get("sellingPrice"), raw.get("selling_price"),
        raw.get("offerPrice"), raw.get("mrp"), raw.get("MRP"),
    ))


def _extract_mrp(raw: dict) -> float | None:
    return _to_float(_first(raw.get("mrp"), raw.get("MRP"), raw.get("originalPrice")))


def _extract_image(raw: dict) -> str | None:
    variants = raw.get("variants")
    if isinstance(variants, list) and variants:
        fv = variants[0]
        if isinstance(fv, dict):
            imgs = fv.get("images")
            if isinstance(imgs, list) and imgs:
                return _full_url(imgs[0])
    return _image_url(_first(
        raw.get("imageUrl"), raw.get("image_url"), raw.get("image"), raw.get("images"),
        raw.get("thumbnail"), raw.get("thumbImage"), raw.get("primaryImage"), raw.get("coverImage"),
    ))


def _extract_url(raw: dict) -> str | None:
    slugs = raw.get("slugs")
    if isinstance(slugs, list) and slugs:
        return f"https://joyory.com/product/{slugs[0]}"
    path = _first(
        raw.get("url"), raw.get("productUrl"), raw.get("product_url"),
        raw.get("permalink"), raw.get("slug"), raw.get("handle"),
    )
    if path and path.startswith("http"):
        return path
    if path:
        return "https://joyory.com/" + path.lstrip("/")
    return None


def _extract_rating(raw: dict) -> tuple[float | None, int | None]:
    count = _to_int(_first(
        raw.get("totalRatings"), raw.get("ratingCount"), raw.get("rating_count"),
        raw.get("reviewCount"), raw.get("numReviews"),
    ))
    if count == 0:
        return None, 0  # no reviews → null rating, not 0.0
    rating = _to_float(_first(raw.get("avgRating"), raw.get("averageRating")))
    if rating is None:
        rating_obj = raw.get("rating") or raw.get("ratings")
        if isinstance(rating_obj, dict):
            rating = _to_float(_first(
                rating_obj.get("average"), rating_obj.get("value"), rating_obj.get("score")
            ))
            if count is None:
                count = _to_int(_first(rating_obj.get("count"), rating_obj.get("total")))
        elif isinstance(rating_obj, (int, float, str)):
            rating = _to_float(rating_obj)
    return rating, count


def _extract_stock(raw: dict) -> bool | None:
    v = _first(
        raw.get("inStock"), raw.get("in_stock"), raw.get("available"),
        raw.get("availability"), raw.get("inventory"), raw.get("stock"), raw.get("stockStatus"),
    )
    if v is not None:
        return _to_bool_stock(v)
    variants = raw.get("variants")
    if isinstance(variants, list) and variants:
        return any(
            vt.get("status") == "inStock" or (isinstance(vt.get("stock"), int) and vt["stock"] > 0)
            for vt in variants if isinstance(vt, dict)
        )
    return None


def _extract_category(raw: dict) -> tuple[str | None, str | None]:
    """Return (name, slug) of the most-specific (longest slug) category."""
    cats = raw.get("categories")
    if isinstance(cats, list) and cats:
        best = max(
            (c for c in cats if isinstance(c, dict) and c.get("name")),
            key=lambda c: len(c.get("slug") or ""),
            default=None,
        )
        if best:
            return best.get("name"), best.get("slug")
    cat = raw.get("category")
    if isinstance(cat, dict):
        return cat.get("name"), cat.get("slug")
    if isinstance(cat, str):
        return cat, None
    return None, None


def _extract_size(raw: dict) -> str | None:
    # "l" alone would match inside "ml"; check for " l" or "l " to require a word boundary
    _UNITS = ("ml", "g", "gm", "oz", "kg", " l", "l ")
    variants = raw.get("variants")
    if isinstance(variants, list) and variants:
        v = variants[0]
        if isinstance(v, dict):
            shade = v.get("shadeName") or v.get("variantSize")
            if shade and any(u in str(shade).lower() for u in _UNITS):
                return str(shade)
    shade_opts = raw.get("shadeOptions")
    if isinstance(shade_opts, list) and shade_opts:
        name = shade_opts[0].get("name", "") if isinstance(shade_opts[0], dict) else ""
        if name and any(u in name.lower() for u in _UNITS):
            return name
    return None


def _price_per_100ml(price: float | None, size_str: str | None) -> float | None:
    if price is None or not size_str:
        return None
    m = re.search(r"([\d.]+)\s*(ml|g|gm)\b", size_str, re.IGNORECASE)
    if not m:
        return None
    qty = float(m.group(1))
    return round(price * 100 / qty, 2) if qty > 0 else None


# ── Contamination detection ───────────────────────────────────────────────────
# Must be defined before normalize_product / normalize_product_detail call it.

_CONTAMINATION_SIGNALS: tuple[str, ...] = (
    "i would ", "so i would", "so i'd", "in my opinion", "i think",
    "user consensus", "currently only", "brand claim", "the brand claims",
    "as an ai", "as a language model",
    "the brand's current faq", "scraped", "according to the faq",
    "this review", "one reviewer", "the reviewer",
    "treat the", "claim as a brand claim",
)


def _detect_contamination(text: str) -> str | None:
    """Return a warning if the description contains leaked AI/review text, else None."""
    if not text:
        return None
    t = text.lower()
    hit = next((s for s in _CONTAMINATION_SIGNALS if s in t), None)
    if hit:
        return (
            f"description_warning: possible AI/review text leak (phrase: '{hit.strip()}'). "
            "Prefer ingredients/attributes fields."
        )
    return None


# ── Tag extraction ────────────────────────────────────────────────────────────

_CONCERN_KEYWORDS: dict[str, list[str]] = {
    "fragrance-free": ["fragrance-free", "fragrance free", "no fragrance", "unscented"],
    "sulfate-free":   ["sulfate-free", "sulfate free", "sls-free", "sls free"],
    "paraben-free":   ["paraben-free", "paraben free"],
    "alcohol-free":   ["alcohol-free", "alcohol free"],
    "oily-skin":      ["oily skin", "oily and acne", "acne-prone", "acne prone", "oil-free", "oil free"],
    "dry-skin":       ["dry skin", "for dry"],
    "sensitive-skin": ["sensitive skin", "for sensitive"],
    "combination-skin": ["combination skin"],
    "anti-aging":     ["anti-aging", "anti-ageing", "mature skin", "anti age", "wrinkle"],
    "brightening":    ["brightening", "vitamin c", "niacinamide", "glow"],
    "hydrating":      ["hydrating", "hyaluronic acid", "moisturizing", "moisture"],
    "spf":            ["spf", "sunscreen", "uva", "uvb"],
    "exfoliating":    ["salicylic acid", "glycolic acid", "aha", "bha", "exfoliat"],
    "unisex":         ["unisex", "for men", "for women", "gender neutral"],
    "vegan":          ["vegan"],
    "cruelty-free":   ["cruelty-free", "cruelty free"],
}


def _extract_tags(raw: dict, description: str | None = None, name: str | None = None) -> list[str]:
    tags: set[str] = set()
    skin_types = raw.get("skinTypes", [])
    if isinstance(skin_types, list):
        for st in skin_types:
            if isinstance(st, dict):
                slug = st.get("slug", "")
                tag_name = st.get("name", "")
                tags.add(slug.replace("+", "-").lower() if slug else tag_name.lower().replace(" ", "-"))

    categories = raw.get("categories", [])
    if isinstance(categories, list):
        for c in categories:
            if isinstance(c, dict) and c.get("slug"):
                tags.add(c["slug"].lower())

    haystack = " ".join(filter(None, [name, description])).lower()
    for tag, keywords in _CONCERN_KEYWORDS.items():
        if any(kw in haystack for kw in keywords):
            tags.add(tag)

    ingredients = raw.get("ingredients", [])
    if isinstance(ingredients, list):
        ing_str = " ".join(str(i).lower() for i in ingredients)
        for kw, tag in (
            ("niacinamide",   "niacinamide"),
            ("hyaluronic",    "hyaluronic-acid"),
            ("retinol",       "retinol"),
            ("retinoid",      "retinol"),
            ("salicylic",     "salicylic-acid"),
            ("vitamin c",     "vitamin-c"),
            ("ascorbic",      "vitamin-c"),
            ("spf",           "spf"),
            ("sunscreen",     "spf"),
        ):
            if kw in ing_str:
                tags.add(tag)

    return sorted(tags)


# ── Ingredient classification ─────────────────────────────────────────────────

_INCI_FILLERS: frozenset[str] = frozenset({
    "aqua", "water", "cyclopentasiloxane", "cyclohexasiloxane", "dimethicone",
    "phenoxyethanol", "ethylhexylglycerin", "glycerin", "glycerine",
    "propylene glycol", "butylene glycol", "carbomer", "xanthan gum",
    "cetyl alcohol", "stearyl alcohol", "cetearyl alcohol",
    "sodium hydroxide", "potassium hydroxide", "triethanolamine",
    "titanium dioxide", "zinc oxide", "octocrylene", "octyl salicylate",
    "homosalate", "avobenzone", "benzophenone", "disodium edta", "tocopherol",
    "citric acid", "lactic acid", "sodium pca", "panthenol",
    "isopropyl myristate", "isocetyl palmitate", "cetearyloctanoate",
    "white oil", "mineral oil", "pib", "pearl pigment", "colorant",
    "dibutyl lauroyl glutamide", "dibutyl ethylhexanoyl glutamide",
    "isostearyl alcohol", "2-octyldodecan-1-ol",
})

_FRAGRANCE_INCI: frozenset[str] = frozenset({
    "fragrance", "parfum", "perfume", "linalool", "limonene", "geraniol",
    "citronellol", "eugenol", "coumarin", "benzyl alcohol", "benzyl benzoate",
    "benzyl salicylate", "cinnamal", "cinnamyl alcohol", "farnesol",
    "hydroxycitronellal", "isoeugenol", "amyl cinnamal",
})

# Substrings that indicate the ingredient is a fragrance-free marker
_FRAGRANCE_FREE_SUBSTRINGS: tuple[str, ...] = ("allergen free fragrance", "fragrance free")


def _classify_ingredients(ing_list: list[str]) -> tuple[list[str], bool | None, bool]:
    """Return (key_ingredients, fragrance_free, inci_complete)."""
    if not ing_list:
        return [], None, False

    lowered = [i.lower().strip() for i in ing_list]
    filler_hits = sum(1 for i in lowered if i in _INCI_FILLERS)
    inci_complete = len(ing_list) >= 5 and filler_hits >= 1

    # O(n) fragrance scan — check each lowered ingredient once
    has_frag = False
    has_frag_free = False
    for low in lowered:
        if any(sub in low for sub in _FRAGRANCE_FREE_SUBSTRINGS):
            has_frag_free = True
            break
        if low in _FRAGRANCE_INCI:
            has_frag = True

    if has_frag_free:
        fragrance_free: bool | None = True
    elif has_frag:
        fragrance_free = False
    else:
        fragrance_free = True if inci_complete else None

    if inci_complete:
        key_ingredients = [ing_list[i] for i, low in enumerate(lowered) if low not in _INCI_FILLERS][:8]
    else:
        key_ingredients = [i for i in ing_list if i][:8]

    return key_ingredients, fragrance_free, inci_complete


def _extract_attributes(raw: dict) -> ProductAttributes:
    skin_types: list[str] = []
    for st in (raw.get("skinTypes") or []):
        if isinstance(st, dict) and st.get("name"):
            skin_types.append(st["name"])

    formulation: str | None = None
    form_raw = raw.get("formulation")
    if isinstance(form_raw, dict):
        formulation = form_raw.get("name")
    elif isinstance(form_raw, str):
        formulation = form_raw

    name = _extract_name(raw)
    desc = raw.get("description", "") or ""
    haystack = f"{name} {desc}".lower()

    spf: str | None = None
    m = re.search(r"spf\s*(\d+)(?:\s*(pa\+{1,4}))?", haystack, re.IGNORECASE)
    if m:
        spf = f"SPF {m.group(1)}" + (f" {m.group(2).upper()}" if m.group(2) else "")

    finish: str | None = None
    for f in ("matte", "glossy", "dewy", "glitter", "shimmer", "satin", "natural"):
        if f in haystack:
            finish = f
            break

    ing_raw = raw.get("ingredients", [])
    ing_list = [str(i).strip() for i in (ing_raw if isinstance(ing_raw, list) else []) if i]
    key_ingredients, fragrance_free_from_ing, inci_complete = _classify_ingredients(ing_list)

    desc_says_ff = any(kw in haystack for kw in ("fragrance-free", "fragrance free", "no fragrance", "unscented"))
    if fragrance_free_from_ing is not None:
        fragrance_free: bool | None = fragrance_free_from_ing
    elif desc_says_ff:
        fragrance_free = True
    elif "fragrance" in haystack:
        fragrance_free = False
    else:
        fragrance_free = None

    _CONCERN_MAP = {
        "Acne Prone": "acne-prone", "Oily": "oily-skin", "Dry": "dry-skin",
        "Sensitive": "sensitive-skin", "Combination": "combination-skin",
    }
    concerns = [_CONCERN_MAP[st] for st in skin_types if st in _CONCERN_MAP]

    return ProductAttributes(
        skin_types=skin_types, concerns=concerns, formulation=formulation,
        spf=spf, fragrance_free=fragrance_free, finish=finish,
        key_ingredients=key_ingredients, inci_complete=inci_complete,
    )


# ── Short description helper ──────────────────────────────────────────────────

def _make_short_desc(desc_str: str | None) -> tuple[str | None, str | None]:
    """Return (short_desc, contamination_warning). Suppresses short_desc if contaminated."""
    if not desc_str:
        return None, None
    warning = _detect_contamination(desc_str)
    if warning:
        return None, warning
    short = (desc_str[:150].rsplit(" ", 1)[0] + "…") if len(desc_str) > 150 else desc_str
    return short, None


# ── Public normalizers ────────────────────────────────────────────────────────

def normalize_product(raw: dict) -> ProductSummary:
    """Convert a raw product dict into ProductSummary."""
    rating, rating_count = _extract_rating(raw)
    cat_name, cat_slug = _extract_category(raw)
    size = _extract_size(raw)
    price = _extract_price(raw)
    name = _extract_name(raw)
    desc = _first(raw.get("description"), raw.get("shortDescription"), raw.get("short_description"))
    desc_str = str(desc) if desc else None
    short_desc, _ = _make_short_desc(desc_str)

    return ProductSummary(
        id=_extract_id(raw),
        name=name,
        brand=_extract_brand(raw),
        category=cat_name,
        category_slug=cat_slug,
        size=size,
        price=price,
        mrp=_extract_mrp(raw),
        currency="INR",
        price_per_100ml=_price_per_100ml(price, size),
        short_description=short_desc,
        tags=_extract_tags(raw, desc_str, name),
        rating=rating,
        rating_count=rating_count,
        in_stock=_extract_stock(raw),
        url=_extract_url(raw),
        image_url=_extract_image(raw),
    )


def normalize_search_response(raw_list: list[dict]) -> list[ProductSummary]:
    """Normalize a list of raw product dicts, skipping malformed items."""
    results = []
    for item in raw_list:
        try:
            if isinstance(item, dict):
                results.append(normalize_product(item))
        except Exception:
            pass
    return results


def normalize_product_detail(raw: dict) -> ProductDetail:
    """Convert a raw product dict into ProductDetail."""
    rating, rating_count = _extract_rating(raw)
    cat_name, cat_slug = _extract_category(raw)
    size = _extract_size(raw)
    price = _extract_price(raw)
    name = _extract_name(raw)

    # Ingredients
    ingredients_raw = _first(
        raw.get("ingredients"), raw.get("ingredientsList"),
        raw.get("ingredients_list"), raw.get("composition"),
    )
    if isinstance(ingredients_raw, str):
        ingredients = [i.strip() for i in re.split(r"[,\n]", ingredients_raw) if i.strip()]
    elif isinstance(ingredients_raw, list):
        ingredients = [str(i).strip() for i in ingredients_raw if i]
    else:
        ingredients = []

    # Images — Joyory stores them inside variants
    imgs_raw = _first(raw.get("images"), raw.get("imageUrls"), raw.get("gallery"), raw.get("mediaGallery"))
    images: list[str] = []
    if isinstance(imgs_raw, list) and imgs_raw:
        images = [u for u in (_full_url(i) for i in imgs_raw) if u]
    if not images:
        seen: set[str] = set()
        for v in (raw.get("variants") or []):
            if isinstance(v, dict):
                for img in (v.get("images") or []):
                    u = _full_url(img)
                    if u and u not in seen:
                        seen.add(u)
                        images.append(u)
    if not images:
        single = _extract_image(raw)
        if single:
            images = [single]

    # Variants
    _SIZE_UNITS = ("ml", "g", "oz")
    variants: list[VariantInfo] = []
    for v in (raw.get("variants") or raw.get("variations") or raw.get("options") or raw.get("skus") or [])[:20]:
        if not isinstance(v, dict):
            continue
        v_stock = _to_bool_stock(_first(
            v.get("inStock"), v.get("available"), v.get("stock"), v.get("status"), v.get("isActive")
        ))
        status = v.get("status")
        if status == "inStock":
            v_stock = True
        elif status in ("outOfStock", "out_of_stock"):
            v_stock = False

        shade = str(_first(v.get("shadeName"), v.get("name"), v.get("label"), v.get("title")) or "")
        v_size = str(v.get("variantSize") or "") or None
        hex_color = str(v.get("hex") or "") or None
        v_imgs = v.get("images") or []
        v_img = _full_url(v_imgs[0]) if isinstance(v_imgs, list) and v_imgs else None

        variants.append(VariantInfo(
            id=str(v.get("sku") or v.get("id") or ""),
            name=shade or v_size,
            size=v_size or (shade if shade and any(u in shade.lower() for u in _SIZE_UNITS) else None),
            shade=shade if shade and not any(u in shade.lower() for u in _SIZE_UNITS) else None,
            hex_color=hex_color if hex_color and hex_color != "#" else None,
            price=_to_float(_first(v.get("discountedPrice"), v.get("price"), v.get("displayPrice"))),
            mrp=_to_float(_first(v.get("mrp"), v.get("originalPrice"))),
            in_stock=v_stock,
            sku=str(v.get("sku") or ""),
            image_url=v_img,
        ))

    desc = _first(
        raw.get("description"), raw.get("shortDescription"), raw.get("short_description"),
        raw.get("productDescription"), raw.get("about"), raw.get("details"),
    )
    desc_str = str(desc) if desc else None
    short_desc, contamination_warning = _make_short_desc(desc_str)

    how_to = _first(
        raw.get("howToUse"), raw.get("how_to_use"), raw.get("directions"),
        raw.get("usage"), raw.get("applicationMethod"),
    )
    if isinstance(how_to, list):
        how_to = " ".join(str(h).strip() for h in how_to if h)

    return ProductDetail(
        id=_extract_id(raw),
        name=name,
        brand=_extract_brand(raw),
        category=cat_name,
        category_slug=cat_slug,
        size=size,
        price=price,
        mrp=_extract_mrp(raw),
        currency="INR",
        short_description=short_desc,
        description=desc_str,
        description_warning=contamination_warning,
        ingredients=ingredients,
        how_to_use=str(how_to) if how_to else None,
        attributes=_extract_attributes(raw),
        rating=rating,
        rating_count=rating_count,
        in_stock=_extract_stock(raw),
        images=images,
        url=_extract_url(raw),
        tags=_extract_tags(raw, desc_str, name),
        variants=variants,
    )


# ── Product detection ─────────────────────────────────────────────────────────

# Module-level constant — rebuilt once, not on every call.
_PRODUCT_FIELDS: frozenset[str] = frozenset({
    "_id", "id", "productId", "product_id", "sku",
    "name", "title", "productName",
    "price", "salePrice", "mrp", "sellingPrice", "discountedPrice",
    "brand", "brandName",
    "image", "imageUrl", "images",
    "slug", "slugs", "handle", "url",
    "stock", "inStock", "inventory",
    "rating", "avgRating",
    "variants", "description",
})


def looks_like_product(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    return sum(1 for f in _PRODUCT_FIELDS if f in obj) >= 3


def extract_products_from_response(data: Any) -> list[dict]:
    """Extract a product list from any common JSON envelope shape."""
    if isinstance(data, list):
        return data if all(looks_like_product(i) for i in data[:3]) else []

    if not isinstance(data, dict):
        return []

    for key in (
        "products", "items", "results", "productsData", "content", "hits",
        "records", "list", "productList", "product_list", "productResults",
        "searchResults", "edges",
    ):
        val = data.get(key)
        if not isinstance(val, list) or not val:
            continue
        if key == "edges":
            nodes = [e.get("node", e) for e in val if isinstance(e, dict)]
            if any(looks_like_product(n) for n in nodes[:3]):
                return nodes
        if any(looks_like_product(i) for i in val[:3]):
            return val

    # One level deeper — but skip "data" here to avoid re-processing it
    # (we already checked data.get("data") above via the loop key)
    for top_key in ("response", "result", "payload"):
        nested = data.get(top_key)
        if isinstance(nested, dict):
            found = extract_products_from_response(nested)
            if found:
                return found

    # "data" key handled separately — it appears in both the outer loop AND
    # as a nesting wrapper, so check it last to avoid double-processing.
    nested_data = data.get("data")
    if isinstance(nested_data, dict):
        found = extract_products_from_response(nested_data)
        if found:
            return found

    return [data] if looks_like_product(data) else []


# ── Relevance scoring ─────────────────────────────────────────────────────────

def score_relevance(product: ProductSummary, query: str) -> tuple[int, str]:
    """Return (score 0-100, match_label) for how well product matches query."""
    q = query.lower().strip()
    if not q:
        return 10, "weak"

    words = q.split()
    name = (product.name or "").lower()
    cat = (product.category or "").lower()
    cat_slug = (product.category_slug or "").lower()
    brand = (product.brand or "").lower()
    desc = (product.short_description or "").lower()
    tags = " ".join(product.tags).lower()

    if q in name:
        return 100, "exact"
    if all(w in name for w in words):
        return 90, "exact"
    if q in cat or q in cat_slug or all(w in cat_slug for w in words):
        return 80, "exact"
    if q == brand or q in brand:
        return 75, "exact"

    matched = sum(1 for w in words if w in name)
    if matched >= len(words) - 1 and len(words) > 1:
        return 60 + matched * 5, "partial"
    if any(w in desc or w in tags for w in words):
        return 30 + matched * 5, "partial"

    return 10, "weak"
