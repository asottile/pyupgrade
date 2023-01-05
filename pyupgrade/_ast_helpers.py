from __future__ import annotations

import ast
import warnings
from typing import Container

from tokenize_rt import Offset


def ast_parse(contents_text: str) -> ast.Module:
    # intentionally ignore warnings, we might be fixing warning-ridden syntax
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return ast.parse(contents_text.encode())


def ast_to_offset(node: ast.expr | ast.stmt) -> Offset:
    return Offset(node.lineno, node.col_offset)


def is_name_attr(
        node: ast.AST,
        imports: dict[str, set[str]],
        mods: tuple[str, ...],
        names: Container[str],
) -> bool:
    return (
        isinstance(node, ast.Name) and
        node.id in names and
        any(node.id in imports[mod] for mod in mods)
    ) or (
        isinstance(node, ast.Attribute) and
        isinstance(node.value, ast.Name) and
        node.value.id in mods and
        node.attr in names
    )


def has_starargs(call: ast.Call) -> bool:
    return (
        any(k.arg is None for k in call.keywords) or
        any(isinstance(a, ast.Starred) for a in call.args)
    )


def contains_await(node: ast.AST) -> bool:
    return any(isinstance(node_, ast.Await) for node_ in ast.walk(node))


def is_async_listcomp(node: ast.ListComp) -> bool:
    return (
        any(gen.is_async for gen in node.generators) or
        contains_await(node)
    )
