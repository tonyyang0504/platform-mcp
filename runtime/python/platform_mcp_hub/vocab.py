"""Category verb vocabularies: the tools every platform in a category exposes, with their input
and output schemas and annotations. The single source is the catalog's ``schema/vocab.json``
(catalog.py finds it: installed package data, or the checkout)."""

from . import catalog, generic


def load_all() -> dict:
    return catalog.vocab()


def vocab_for(spec: dict) -> dict:
    """The verbs for this spec's category: a generic entry's own tool definitions (generic.py), embedded in the spec,
    else the catalog's vocabulary."""
    if generic.is_generic(spec):
        return generic.vocab(spec)
    if isinstance(spec.get("vocab"), dict) and spec["vocab"]:
        return spec["vocab"]
    return load_all()[spec["category"]]
