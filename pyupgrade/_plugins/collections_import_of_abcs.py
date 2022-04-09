from __future__ import annotations

import ast
import collections.abc
import itertools
from typing import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade._ast_helpers import ast_to_offset
from pyupgrade._data import register
from pyupgrade._data import State
from pyupgrade._data import TokenFunc
from pyupgrade._token_helpers import find_token


_ABC_NAMES = {nm for nm in dir(collections.abc) if not nm.startswith('_')}


def _find_token_at_line(tokens: list[Token], line_number: int) -> int | None:
    for i, token in enumerate(tokens):
        if token.line >= line_number:
            break
    else:
        return None

    return i


def _find_token_at_next_line(tokens: list[Token], line_number: int) -> int | None:
    for i, token in enumerate(tokens):
        if token.line > line_number:
            break
    else:
        return None

    return i


def _remove_line(tokens: list[Token], line_number: int) -> int:
    remove_start = _find_token_at_line(tokens, line_number)
    remove_end = _find_token_at_next_line(tokens, line_number)
    for token in tokens[remove_end:]:
        token._replace(line=token.line - 1)
    del tokens[remove_start:remove_end]
    return remove_start


def _insert_line(tokens: list[Token], line_number: int) -> int:
    insert_point = _find_token_at_line(tokens, line_number)
    for token in tokens[insert_point:]:
        token._replace(line=token.line + 1)

    return insert_point


def _copy_line(tokens: list[Token], line_number: int) -> list[Token]:
    return [t for t in tokens if t.line == line_number]


def _handle_collections_import_of_abcs(
        i: int,
        tokens: list[Token],
) -> None:
    j = find_token(tokens, i, 'collections')
    tokens_line = tokens[j].line

    orig_tokens = _copy_line(tokens, tokens_line)
    while orig_tokens[0].name == 'DEDENT':
        del orig_tokens[0]

    if any(t.name == 'ESCAPED_NL' or t.name == 'OP' and t.src == '(' for t in orig_tokens):
        return

    # does not handle importing with 'as', as in "from collections import Mapping as MappingABC"
    # does not handle importing multiline, either by enclosing names in ()'s or using '\' continuations
    imported_name_tokens = [t for t in itertools.takewhile(lambda tk: tk.name != 'NEWLINE', tokens[j+1:])
                            if t.name == 'NAME' and t.src != 'import']
    imported_names = set(t.src for t in imported_name_tokens)
    if "as" in imported_names:
        return

    if not _ABC_NAMES & imported_names:
        return

    if _ABC_NAMES > imported_names:
        tokens[j] = tokens[j]._replace(src='collections.abc')
    else:
        # use set operations to separate ABC's from non-ABCs that are still in collections module
        abc_names = imported_names & _ABC_NAMES
        coll_names = imported_names - abc_names

        remaining_tokens = tokens[i + len(orig_tokens):]
        abc_tokens = orig_tokens[:]

        def _get_list_indices_for_names(toks, search_set):
            base = [i for i, t in enumerate(toks) if t.src in search_set]
            extras = []
            for index in base:
                for ii, t in enumerate(toks[index - 1::-1], start=1):
                    if t.name not in {'OP', 'UNIMPORTANT_WS'}:
                        break
                    extras.append(index - ii)
            return sorted(base + extras)

        # remove abc_names from first line
        drops = _get_list_indices_for_names(orig_tokens, abc_names)
        for d in drops[::-1]:
            del orig_tokens[d]

        # remove coll_names from second line
        drops = _get_list_indices_for_names(abc_tokens, coll_names)
        for d in drops[::-1]:
            del abc_tokens[d]

        # remove spurious comma after import if found
        def _remove_spurious_comma_after_import(tokens):
            try:
                comma_loc = find_token(tokens, 0, ',')
            except IndexError:
                pass
            else:
                if tokens[comma_loc-1].src == 'import':
                    del tokens[comma_loc]

        _remove_spurious_comma_after_import(orig_tokens)
        _remove_spurious_comma_after_import(abc_tokens)

        # create a NEWLINE token, with appropriate src and utf_byte_offset values
        added_utf8_bytes = sum(t.utf8_byte_offset for t in orig_tokens)
        # not sure why this has to be this way, but it does
        added_newline_src = {'\n': '', '': '\n'}[orig_tokens[-1].src]
        newline_token = Token(name='NEWLINE',
                              src=added_newline_src,
                              line=tokens_line,
                              utf8_byte_offset=added_utf8_bytes)

        insert_loc = _remove_line(tokens, tokens_line)
        _insert_line(tokens, tokens_line)
        _insert_line(tokens, tokens_line)
        if remaining_tokens:
            remaining_tokens.insert(
                0,
                Token(
                    name="UNIMPORTANT_WS",
                    line=remaining_tokens[0].line,
                    utf8_byte_offset=0,
                    src=" " * remaining_tokens[0].utf8_byte_offset,
                ))
        tokens[:] = tokens[:insert_loc] + orig_tokens + [newline_token] + abc_tokens + remaining_tokens

        # update collections -> collections.abc in abc_tokens
        jj = find_token(tokens, j+len(orig_tokens), 'collections')
        tokens[jj] = tokens[jj]._replace(src='collections.abc')


@register(ast.ImportFrom)
def visit_ImportFrom(
        state: State,
        node: ast.ImportFrom,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    if (
            state.settings.min_version >= (3,) and
            node.module == 'collections' and
            node.level == 0
    ):
        yield ast_to_offset(node), _handle_collections_import_of_abcs
