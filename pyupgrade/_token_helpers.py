import ast
import keyword
import sys
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import Sequence
from typing import Tuple

from tokenize_rt import NON_CODING_TOKENS
from tokenize_rt import Token
from tokenize_rt import tokens_to_src
from tokenize_rt import UNIMPORTANT_WS

BRACES = {'(': ')', '[': ']', '{': '}'}
OPENING, CLOSING = frozenset(BRACES), frozenset(BRACES.values())
KEYWORDS = frozenset(keyword.kwlist)


def immediately_paren(func: str, tokens: List[Token], i: int) -> bool:
    return tokens[i].src == func and tokens[i + 1].src == '('


class Victims(NamedTuple):
    starts: List[int]
    ends: List[int]
    first_comma_index: Optional[int]
    arg_index: int


def _search_until(tokens: List[Token], idx: int, arg: ast.expr) -> int:
    while (
            idx < len(tokens) and
            not (
                tokens[idx].line == arg.lineno and
                tokens[idx].utf8_byte_offset == arg.col_offset
            )
    ):
        idx += 1
    return idx


def find_token(tokens: List[Token], i: int, src: str) -> int:
    while tokens[i].src != src:
        i += 1
    return i


def find_open_paren(tokens: List[Token], i: int) -> int:
    return find_token(tokens, i, '(')


def find_end(tokens: List[Token], i: int) -> int:
    while tokens[i].name not in {'NEWLINE', 'ENDMARKER'}:
        i += 1

    # depending on the version of python, some will not emit
    # NEWLINE('') at the end of a file which does not end with a
    # newline (for example 3.6.5)
    if tokens[i].name == 'ENDMARKER':  # pragma: no cover
        i -= 1
    else:
        i += 1

    return i


if sys.version_info >= (3, 8):  # pragma: >=3.8 cover
    # python 3.8 fixed the offsets of generators / tuples
    def _arg_token_index(tokens: List[Token], i: int, arg: ast.expr) -> int:
        idx = _search_until(tokens, i, arg) + 1
        while idx < len(tokens) and tokens[idx].name in NON_CODING_TOKENS:
            idx += 1
        return idx
else:  # pragma: <3.8 cover
    def _arg_token_index(tokens: List[Token], i: int, arg: ast.expr) -> int:
        # lists containing non-tuples report the first element correctly
        if isinstance(arg, ast.List):
            # If the first element is a tuple, the ast lies to us about its col
            # offset.  We must find the first `(` token after the start of the
            # list element.
            if isinstance(arg.elts[0], ast.Tuple):
                i = _search_until(tokens, i, arg)
                return find_open_paren(tokens, i)
            else:
                return _search_until(tokens, i, arg.elts[0])
            # others' start position points at their first child node already
        else:
            return _search_until(tokens, i, arg)


def victims(
        tokens: List[Token],
        start: int,
        arg: ast.expr,
        gen: bool,
) -> Victims:
    starts = [start]
    start_depths = [1]
    ends: List[int] = []
    first_comma_index = None
    arg_depth = None
    arg_index = _arg_token_index(tokens, start, arg)
    brace_stack = [tokens[start].src]
    i = start + 1

    while brace_stack:
        token = tokens[i].src
        is_start_brace = token in BRACES
        is_end_brace = token == BRACES[brace_stack[-1]]

        if i == arg_index:
            arg_depth = len(brace_stack)

        if is_start_brace:
            brace_stack.append(token)

        # Remove all braces before the first element of the inner
        # comprehension's target.
        if is_start_brace and arg_depth is None:
            start_depths.append(len(brace_stack))
            starts.append(i)

        if (
                token == ',' and
                len(brace_stack) == arg_depth and
                first_comma_index is None
        ):
            first_comma_index = i

        if is_end_brace and len(brace_stack) in start_depths:
            if tokens[i - 2].src == ',' and tokens[i - 1].src == ' ':
                ends.extend((i - 2, i - 1, i))
            elif tokens[i - 1].src == ',':
                ends.extend((i - 1, i))
            else:
                ends.append(i)
            if len(brace_stack) > 1 and tokens[i + 1].src == ',':
                ends.append(i + 1)

        if is_end_brace:
            brace_stack.pop()

        i += 1
    # May need to remove a trailing comma for a comprehension
    if gen:
        i -= 2
        while tokens[i].name in NON_CODING_TOKENS:
            i -= 1
        if tokens[i].src == ',':
            ends.append(i)

    return Victims(starts, sorted(set(ends)), first_comma_index, arg_index)


def find_closing_bracket(tokens: List[Token], i: int) -> int:
    assert tokens[i].src in OPENING
    depth = 1
    i += 1
    while depth:
        if tokens[i].src in OPENING:
            depth += 1
        elif tokens[i].src in CLOSING:
            depth -= 1
        i += 1
    return i - 1


def find_block_start(tokens: List[Token], i: int) -> int:
    depth = 0
    while depth or tokens[i].src != ':':
        if tokens[i].src in OPENING:
            depth += 1
        elif tokens[i].src in CLOSING:
            depth -= 1
        i += 1
    return i


class Block(NamedTuple):
    start: int
    colon: int
    block: int
    end: int
    line: bool

    def _initial_indent(self, tokens: List[Token]) -> int:
        if tokens[self.start].src.isspace():
            return len(tokens[self.start].src)
        else:
            return 0

    def _minimum_indent(self, tokens: List[Token]) -> int:
        block_indent = None
        for i in range(self.block, self.end):
            if (
                    tokens[i - 1].name in ('NL', 'NEWLINE') and
                    tokens[i].name in ('INDENT', UNIMPORTANT_WS) and
                    # comments can have arbitrary indentation so ignore them
                    tokens[i + 1].name != 'COMMENT'
            ):
                token_indent = len(tokens[i].src)
                if block_indent is None:
                    block_indent = token_indent
                else:
                    block_indent = min(block_indent, token_indent)

        assert block_indent is not None
        return block_indent

    def dedent(self, tokens: List[Token]) -> None:
        if self.line:
            return
        initial_indent = self._initial_indent(tokens)
        diff = self._minimum_indent(tokens) - initial_indent
        for i in range(self.block, self.end):
            if (
                    tokens[i - 1].name in ('DEDENT', 'NL', 'NEWLINE') and
                    tokens[i].name in ('INDENT', UNIMPORTANT_WS)
            ):
                # make sure we preserve *at least* the initial indent
                s = tokens[i].src
                s = s[:initial_indent] + s[initial_indent + diff:]
                tokens[i] = tokens[i]._replace(src=s)

    def replace_condition(self, tokens: List[Token], new: List[Token]) -> None:
        start = self.start
        while tokens[start].name == 'UNIMPORTANT_WS':
            start += 1
        tokens[start:self.colon] = new

    def _trim_end(self, tokens: List[Token]) -> 'Block':
        """the tokenizer reports the end of the block at the beginning of
        the next block
        """
        i = last_token = self.end - 1
        while tokens[i].name in NON_CODING_TOKENS | {'DEDENT', 'NEWLINE'}:
            # if we find an indented comment inside our block, keep it
            if (
                    tokens[i].name in {'NL', 'NEWLINE'} and
                    tokens[i + 1].name == UNIMPORTANT_WS and
                    len(tokens[i + 1].src) > self._initial_indent(tokens)
            ):
                break
            # otherwise we've found another line to remove
            elif tokens[i].name in {'NL', 'NEWLINE'}:
                last_token = i
            i -= 1
        return self._replace(end=last_token + 1)

    @classmethod
    def find(
            cls,
            tokens: List[Token],
            i: int,
            trim_end: bool = False,
    ) -> 'Block':
        if i > 0 and tokens[i - 1].name in {'INDENT', UNIMPORTANT_WS}:
            i -= 1
        start = i
        colon = find_block_start(tokens, i)

        j = colon + 1
        while (
                tokens[j].name != 'NEWLINE' and
                tokens[j].name in NON_CODING_TOKENS
        ):
            j += 1

        if tokens[j].name == 'NEWLINE':  # multi line block
            block = j + 1
            while tokens[j].name != 'INDENT':
                j += 1
            level = 1
            j += 1
            while level:
                level += {'INDENT': 1, 'DEDENT': -1}.get(tokens[j].name, 0)
                j += 1
            ret = cls(start, colon, block, j, line=False)
            if trim_end:
                return ret._trim_end(tokens)
            else:
                return ret
        else:  # single line block
            block = j
            j = find_end(tokens, j)
            return cls(start, colon, block, j, line=True)


def _is_on_a_line_by_self(tokens: List[Token], i: int) -> bool:
    return (
        tokens[i - 2].name == 'NL' and
        tokens[i - 1].name == UNIMPORTANT_WS and
        tokens[i + 1].name == 'NL'
    )


def remove_brace(tokens: List[Token], i: int) -> None:
    if _is_on_a_line_by_self(tokens, i):
        del tokens[i - 1:i + 2]
    else:
        del tokens[i]


def remove_base_class(i: int, tokens: List[Token]) -> None:
    # look forward and backward to find commas / parens
    brace_stack = []
    j = i
    while tokens[j].src not in {',', ':'}:
        if tokens[j].src == ')':
            brace_stack.append(j)
        j += 1
    right = j

    if tokens[right].src == ':':
        brace_stack.pop()
    else:
        # if there's a close-paren after a trailing comma
        j = right + 1
        while tokens[j].name in NON_CODING_TOKENS:
            j += 1
        if tokens[j].src == ')':
            while tokens[j].src != ':':
                j += 1
            right = j

    if brace_stack:
        last_part = brace_stack[-1]
    else:
        last_part = i

    j = i
    while brace_stack:
        if tokens[j].src == '(':
            brace_stack.pop()
        j -= 1

    while tokens[j].src not in {',', '('}:
        j -= 1
    left = j

    # single base, remove the entire bases
    if tokens[left].src == '(' and tokens[right].src == ':':
        del tokens[left:right]
    # multiple bases, base is first
    elif tokens[left].src == '(' and tokens[right].src != ':':
        # if there's space / comment afterwards remove that too
        while tokens[right + 1].name in {UNIMPORTANT_WS, 'COMMENT'}:
            right += 1
        del tokens[left + 1:right + 1]
    # multiple bases, base is not first
    else:
        del tokens[left:last_part + 1]


def remove_decorator(i: int, tokens: List[Token]) -> None:
    while tokens[i - 1].src != '@':
        i -= 1
    if i > 1 and tokens[i - 2].name not in {'NEWLINE', 'NL'}:
        i -= 1
    end = i + 1
    while tokens[end].name != 'NEWLINE':
        end += 1
    del tokens[i - 1:end + 1]


def parse_call_args(
        tokens: List[Token],
        i: int,
) -> Tuple[List[Tuple[int, int]], int]:
    args = []
    stack = [i]
    i += 1
    arg_start = i

    while stack:
        token = tokens[i]

        if len(stack) == 1 and token.src == ',':
            args.append((arg_start, i))
            arg_start = i + 1
        elif token.src in BRACES:
            stack.append(i)
        elif token.src == BRACES[tokens[stack[-1]].src]:
            stack.pop()
            # if we're at the end, append that argument
            if not stack and tokens_to_src(tokens[arg_start:i]).strip():
                args.append((arg_start, i))

        i += 1

    return args, i


def arg_str(tokens: List[Token], start: int, end: int) -> str:
    return tokens_to_src(tokens[start:end]).strip()


def _arg_contains_newline(tokens: List[Token], start: int, end: int) -> bool:
    while tokens[start].name in {'NL', 'NEWLINE', UNIMPORTANT_WS}:
        start += 1
    for i in range(start, end):
        if tokens[i].name in {'NL', 'NEWLINE'}:
            return True
    else:
        return False


def replace_call(
        tokens: List[Token],
        start: int,
        end: int,
        args: List[Tuple[int, int]],
        tmpl: str,
        *,
        parens: Sequence[int] = (),
) -> None:
    arg_strs = [arg_str(tokens, *arg) for arg in args]
    for paren in parens:
        arg_strs[paren] = f'({arg_strs[paren]})'

    # there are a few edge cases which cause syntax errors when the first
    # argument contains newlines (especially when moved outside of a natural
    # contiunuation context)
    if _arg_contains_newline(tokens, *args[0]) and 0 not in parens:
        # this attempts to preserve more of the whitespace by using the
        # original non-stripped argument string
        arg_strs[0] = f'({tokens_to_src(tokens[slice(*args[0])])})'

    start_rest = args[0][1] + 1
    while (
            start_rest < end and
            tokens[start_rest].name in {'COMMENT', UNIMPORTANT_WS}
    ):
        start_rest += 1

    # Remove trailing comma
    end_rest = end - 1
    while (
            tokens[end_rest - 1].name == 'OP' and
            tokens[end_rest - 1].src == ','
    ):
        end_rest -= 1

    rest = tokens_to_src(tokens[start_rest:end_rest])
    src = tmpl.format(args=arg_strs, rest=rest)
    tokens[start:end] = [Token('CODE', src)]


def find_and_replace_call(
        i: int,
        tokens: List[Token],
        *,
        template: str,
        parens: Tuple[int, ...] = (),
) -> None:
    j = find_open_paren(tokens, i)
    func_args, end = parse_call_args(tokens, j)
    replace_call(tokens, i, end, func_args, template, parens=parens)


def replace_name(i: int, tokens: List[Token], *, name: str, new: str) -> None:
    # preserve token offset in case we need to match it later
    new_token = tokens[i]._replace(name='CODE', src=new)
    j = i
    while tokens[j].src != name:
        # timid: if we see a parenthesis here, skip it
        if tokens[j].src == ')':
            return
        j += 1
    tokens[i:j + 1] = [new_token]


def delete_argument(
        i: int, tokens: List[Token],
        func_args: Sequence[Tuple[int, int]],
) -> None:
    if i == 0:
        # delete leading whitespace before next token
        end_idx, _ = func_args[i + 1]
        while tokens[end_idx].name == 'UNIMPORTANT_WS':
            end_idx += 1

        del tokens[func_args[i][0]:end_idx]
    else:
        del tokens[func_args[i - 1][1]:func_args[i][1]]


def replace_argument(
        i: int,
        tokens: List[Token],
        func_args: Sequence[Tuple[int, int]],
        *,
        new: str,
) -> None:
    start_idx, end_idx = func_args[i]
    # don't replace leading whitespace / newlines
    while tokens[start_idx].name in {'UNIMPORTANT_WS', 'NL'}:
        start_idx += 1
    tokens[start_idx:end_idx] = [Token('SRC', new)]


def find_comprehension_opening_bracket(i: int, tokens: List[Token]) -> int:
    """Find opening bracket of comprehension given first argument."""
    if sys.version_info < (3, 8):  # pragma: <3.8 cover
        i -= 1
        while not (tokens[i].name == 'OP' and tokens[i].src == '[') and i:
            i -= 1
        return i
    else:  # pragma: >=3.8 cover
        return i


def replace_list_comp_brackets(i: int, tokens: List[Token]) -> None:
    start = find_comprehension_opening_bracket(i, tokens)
    end = find_closing_bracket(tokens, start)
    tokens[end] = Token('OP', ')')
    tokens[start] = Token('OP', '(')
