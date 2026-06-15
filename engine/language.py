"""
Tokeniser, AST nodes, and parser for the formula language.
"""

import re
from typing import List, Optional, Tuple, Union

# ─── Tokeniser ───────────────────────────────────────────────────────

TOKEN_SPEC = [
    ('NUMBER',   r'-?\d+\.?\d*(?:e-?\d+)?'),
    ('SHIFT',    r'\.shift\(\d+\)'),
    ('IDENT',    r'[a-zA-Z_]\w*'),
    ('OP',       r'<=|>=|==|!=|[+\-*/<>&|()]'),
    ('COMMA',    r','),
    ('SKIP',     r'[ \t]+'),
]

TOKEN_RE = re.compile('|'.join(f'(?P<{name}>{pat})' for name, pat in TOKEN_SPEC))


def tokenize(text: str) -> List[Tuple[str, str]]:
    tokens = []
    for m in TOKEN_RE.finditer(text):
        kind = m.lastgroup
        val = m.group()
        if kind == 'SKIP':
            continue
        if kind == 'NUMBER':
            val = float(val) if '.' in val or 'e' in val.lower() else int(val)
        tokens.append((kind, val))
    return tokens


# ─── AST Node Types ──────────────────────────────────────────────────

class Node:
    pass

class Number(Node):
    def __init__(self, value: Union[int, float]): self.value = value
    def __repr__(self): return f'Num({self.value})'

class Ident(Node):
    def __init__(self, name: str): self.name = name
    def __repr__(self): return f'Ident({self.name})'

class Shift(Node):
    def __init__(self, ident: str, n: int, expr: Optional[Node] = None):
        self.ident = ident
        self.n = n
        self.expr = expr
    def __repr__(self): return f'Shift({self.ident}, {self.n})'

    @classmethod
    def _from_node(cls, node: Node, n: int):
        if isinstance(node, Ident):
            return cls(node.name, n)
        if isinstance(node, FuncCall):
            return cls(node.name, n, expr=node)
        if isinstance(node, Number):
            return cls(str(node.value), n)
        return Shift(node.__class__.__name__, n, expr=node)

class UnaryOp(Node):
    def __init__(self, op: str, expr: Node):
        self.op = op
        self.expr = expr
    def __repr__(self): return f'Unary({self.op}, {self.expr})'

class BinOp(Node):
    def __init__(self, op: str, left: Node, right: Node):
        self.op = op
        self.left = left
        self.right = right
    def __repr__(self): return f'BinOp({self.left} {self.op} {self.right})'

class FuncCall(Node):
    def __init__(self, name: str, args: List[Node]):
        self.name = name
        self.args = args
    def __repr__(self): return f'Call({self.name}({self.args}))'


# ─── Parser (Recursive Descent) ──────────────────────────────────────

class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Tuple[str, str]]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Optional[Tuple[str, str]]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, kind: Optional[str] = None) -> Tuple[str, str]:
        tok = self.peek()
        if tok is None:
            raise ParseError('Unexpected end of expression')
        if kind and tok[0] != kind:
            raise ParseError(f'Expected {kind}, got {tok[0]}({tok[1]})')
        self.pos += 1
        return tok

    def parse(self) -> Node:
        return self.parse_or()

    def parse_or(self) -> Node:
        left = self.parse_and()
        while self.peek() and self.peek()[0] == 'OP' and self.peek()[1] == '|':
            self.consume()
            right = self.parse_and()
            left = BinOp('|', left, right)
        return left

    def parse_and(self) -> Node:
        left = self.parse_cmp()
        while self.peek() and self.peek()[0] == 'OP' and self.peek()[1] == '&':
            self.consume()
            right = self.parse_cmp()
            left = BinOp('&', left, right)
        return left

    def parse_cmp(self) -> Node:
        left = self.parse_add()
        while self.peek() and self.peek()[0] == 'OP' and self.peek()[1] in ('<', '>', '<=', '>=', '==', '!='):
            op = self.consume()[1]
            right = self.parse_add()
            left = BinOp(op, left, right)
        return left

    def parse_add(self) -> Node:
        left = self.parse_mul()
        while self.peek() and self.peek()[0] == 'OP' and self.peek()[1] in ('+', '-'):
            op = self.consume()[1]
            right = self.parse_mul()
            left = BinOp(op, left, right)
        return left

    def parse_mul(self) -> Node:
        left = self.parse_unary()
        while self.peek() and self.peek()[0] == 'OP' and self.peek()[1] in ('*', '/'):
            op = self.consume()[1]
            right = self.parse_unary()
            left = BinOp(op, left, right)
        return left

    def parse_unary(self) -> Node:
        if self.peek() and self.peek()[0] == 'OP' and self.peek()[1] == '-':
            self.consume()
            return UnaryOp('-', self.parse_unary())
        return self.parse_primary()

    def _try_shift(self, node: Node) -> Node:
        if self.peek() and self.peek()[0] == 'SHIFT':
            shift_str = self.consume()[1]
            n = int(re.search(r'\d+', shift_str).group())
            return Shift._from_node(node, n)
        return node

    def parse_primary(self) -> Node:
        tok = self.peek()
        if tok is None:
            raise ParseError('Unexpected end of expression')

        if tok[0] == 'NUMBER':
            self.consume()
            return self._try_shift(Number(tok[1]))

        if tok[0] == 'OP' and tok[1] == '(':
            self.consume()
            expr = self.parse_or()
            self.consume('OP')
            return self._try_shift(expr)

        if tok[0] == 'IDENT':
            name = self.consume()[1]
            if self.peek() and self.peek()[0] == 'OP' and self.peek()[1] == '(':
                self.consume()
                args = []
                if not (self.peek() and self.peek()[0] == 'OP' and self.peek()[1] == ')'):
                    args.append(self.parse_or())
                    while self.peek() and self.peek()[0] == 'COMMA':
                        self.consume()
                        args.append(self.parse_or())
                self.consume('OP')
                return self._try_shift(FuncCall(name, args))
            if self.peek() and self.peek()[0] == 'SHIFT':
                shift_str = self.consume()[1]
                n = int(re.search(r'\d+', shift_str).group())
                return Shift(name, n)
            return self._try_shift(Ident(name))

        raise ParseError(f'Unexpected token: {tok}')


def parse(text: str) -> Node:
    tokens = tokenize(text)
    if not tokens:
        raise ParseError('Empty expression')
    parser = Parser(tokens)
    ast = parser.parse()
    if parser.pos < len(tokens):
        raise ParseError(f'Unexpected tokens after expression: {tokens[parser.pos:]}')
    return ast
