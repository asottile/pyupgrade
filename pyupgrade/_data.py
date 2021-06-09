import ast
import collections
import pkgutil
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List
from typing import NamedTuple
from typing import Set
from typing import TYPE_CHECKING
from typing import Tuple
from typing import Type
from typing import TypeVar

from tokenize_rt import Offset
from tokenize_rt import Token

from pyupgrade import _plugins

if TYPE_CHECKING:
    from typing import Protocol
else:
    Protocol = object

Version = Tuple[int, ...]


FIX_FSTRING = 'fstring'
FIX_ESCAPE_SEQUENCES = 'escape_sequences'
FIX_PY3_COMPAT_IMPORT_REMOVALS = 'py3_compat_import_removals'

TOKEN_FIXES = [
    FIX_FSTRING,
    FIX_ESCAPE_SEQUENCES,
    FIX_PY3_COMPAT_IMPORT_REMOVALS,
]


class Settings(NamedTuple):
    min_version: Version = (2, 7)
    keep_percent_format: bool = False
    keep_mock: bool = False
    keep_runtime_typing: bool = False
    fixes_to_exclude: list = []


class State(NamedTuple):
    settings: Settings
    from_imports: Dict[str, Set[str]]
    in_annotation: bool = False


AST_T = TypeVar('AST_T', bound=ast.AST)
TokenFunc = Callable[[int, List[Token]], None]
ASTFunc = Callable[[State, AST_T, ast.AST], Iterable[Tuple[Offset, TokenFunc]]]

RECORD_FROM_IMPORTS = frozenset((
    '__future__',
    'functools',
    'mmap',
    'select',
    'six',
    'socket',
    'subprocess',
    'sys',
    'typing',
))

FUNCS = collections.defaultdict(list)


def register(tp: Type[AST_T]) -> Callable[[ASTFunc[AST_T]], ASTFunc[AST_T]]:
    def register_decorator(func: ASTFunc[AST_T]) -> ASTFunc[AST_T]:
        FUNCS[tp].append(func)
        return func

    return register_decorator


class ASTCallbackMapping(Protocol):
    def __getitem__(self, tp: Type[AST_T]) -> List[ASTFunc[AST_T]]: ...


def visit(
        funcs: ASTCallbackMapping,
        tree: ast.Module,
        settings: Settings,
) -> Dict[Offset, List[TokenFunc]]:
    import_plugins(settings)

    initial_state = State(
        settings=settings,
        from_imports=collections.defaultdict(set),
    )

    nodes: List[Tuple[State, ast.AST, ast.AST]] = [(initial_state, tree, tree)]

    ret = collections.defaultdict(list)
    while nodes:
        state, node, parent = nodes.pop()

        tp = type(node)
        for ast_func in funcs[tp]:
            for offset, token_func in ast_func(state, node, parent):
                ret[offset].append(token_func)

        if (
                isinstance(node, ast.ImportFrom) and
                not node.level and
                node.module in RECORD_FROM_IMPORTS
        ):
            state.from_imports[node.module].update(
                name.name for name in node.names if not name.asname
            )

        for name in reversed(node._fields):
            value = getattr(node, name)
            if name in {'annotation', 'returns'}:
                next_state = state._replace(in_annotation=True)
            else:
                next_state = state

            if isinstance(value, ast.AST):
                nodes.append((next_state, value, node))
            elif isinstance(value, list):
                for value in reversed(value):
                    if isinstance(value, ast.AST):
                        nodes.append((next_state, value, node))
    return ret


def _get_fix_name_from_path(path: str) -> str:
    return path.split('.')[-1]


def _should_import_plugin(settings: Settings, plugin_file_path: str) -> bool:
    return _get_fix_name_from_path(plugin_file_path) not in settings.fixes_to_exclude


def _get_all_plugins():
    plugins_path: str = _plugins.__path__  # type: ignore
    return pkgutil.walk_packages(plugins_path, f'{_plugins.__name__}.')


def get_fix_names() -> list:
    plugin_fixes = [
        _get_fix_name_from_path(name) for _, name, _ in _get_all_plugins()
    ]

    return plugin_fixes + TOKEN_FIXES


def import_plugins(settings: Settings) -> None:
    # https://github.com/python/mypy/issues/1422
    mod_infos = _get_all_plugins()
    for _, name, _ in mod_infos:
        if _should_import_plugin(settings, name):
            __import__(name, fromlist=['_trash'])
