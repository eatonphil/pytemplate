import io


def eval_template(template: str, env: dict) -> str:
    tokens = lex(template)
    ast, _ = parse(tokens)
    with io.StringIO() as memfd:
        interpret(memfd, ast, env)
        return memfd.getvalue()


BLOCK_OPEN = '{%'
BLOCK_CLOSE = '%}'

TAG_OPEN = '{{'
TAG_CLOSE = '}}'


def getelement(source, cursor):
    if cursor < 0:
        return None
    if cursor < len(source):
        return source[cursor]
    return None


def lex(source):
    tokens = []
    current = ''
    cursor = 0
    while cursor < len(source):
        char = getelement(source, cursor)
        if char == '{':
            # Handle escaping {
            if getelement(source, cursor-1) == '{':
                cursor += 1
                continue
            
            next_char = getelement(source, cursor+1)
            if next_char in ['%', '{']:
                if current:
                    tokens.append({
                        'value': current,
                        'cursor': cursor - len(current),
                    })
                    current = ''

                tokens.append({
                    'value': BLOCK_OPEN if next_char == '%' else TAG_OPEN,
                    'cursor': cursor,
                })
                cursor += 2
                continue

        if char in ['%', '}']:
            # Handle escaping % and }
            if getelement(source, cursor-1) == char:
                cursor += 1
                continue

            if getelement(source, cursor+1) != '}':
                cursor += 1
                continue

            if current:
                tokens.append({
                    'value': current,
                    'cursor': cursor - len(current),
                })
                current = ''

            tokens.append({
                'value': BLOCK_CLOSE if char == '%' else TAG_CLOSE,
                'cursor': cursor,
            })
            cursor += 2
            continue

        current += getelement(source, cursor)
        cursor += 1

    if current:
        tokens.append({
            'value': current,
            'cursor': cursor - len(current),
        })

    return tokens


def parse(tokens, end_of_block_marker=None):
    cursor = 0
    ast = []
    while cursor < len(tokens):
        t = getelement(tokens, cursor)
        value = t['value']
        if value == TAG_OPEN:
            if getelement(tokens, cursor+2)['value'] != TAG_CLOSE:
                raise Exception('Expected closing tag')

            node_tokens = lex_node(getelement(tokens, cursor+1)['value'])
            node_ast = parse_node(node_tokens)
            ast.append({
                'type': 'tag',
                'value': node_ast,
            })
            cursor += 3
            continue
        
        if value == TAG_CLOSE:
            raise Exception('Expected opening tag')

        if value == BLOCK_OPEN:
            if getelement(tokens, cursor+2)['value'] != BLOCK_CLOSE:
                raise Exception('Expected end of block open')

            block = getelement(tokens, cursor+1)
            node_tokens = lex_node(block['value'])
            node_ast = parse_node(node_tokens)
            if end_of_block_marker and 'end'+end_of_block_marker == node_ast['value']:
                return ast, cursor+3

            child, cursor_offset = parse(tokens[cursor+3:], node_ast['value'])
            if cursor_offset == 0:
                raise Exception('Failed to find end of block')

            ast.append({
                'type': 'block',
                'value': node_ast,
                'child': child,
            })
            cursor += cursor_offset + 3
            continue

        if value == BLOCK_CLOSE:
            raise Exception('Expected start of block open')

        ast.append({
            'type': 'text',
            'value': t,
        })
        cursor += 1

    return ast, cursor


def lex_node(source):
    tokens = []
    cursor = 0
    current = ''
    while cursor < len(source):
        char = getelement(source, cursor)
        if char in ['\r', '\t', '\n', ' ']:
            if current:
                tokens.append({
                    'value': current,
                    'type': 'literal',
                })
                current = ''

            cursor += 1
            continue

        if char in ['(', ')', ',']:
            if current:
                tokens.append({
                    'value': current,
                    'type': 'literal',
                })
                current = ''

            tokens.append({
                'value': char,
                'type': 'syntax',
            })
            cursor += 1
            continue

        current += char
        cursor +=1

    return tokens


def parse_node(tokens):
    cursor = 0
    ast = None
    while cursor < len(tokens):
        t = getelement(tokens, cursor)
        if t['type'] != 'literal':
            raise Exception('Expected literal')
        cursor += 1

        next_t = getelement(tokens, cursor)
        if not next_t:
            ast = t
            break

        if next_t['value'] != '(':
            ast = t
            break

        cursor += 1

        if next_t['value'] == '(':
            args, cursor = parse_node_args(tokens[cursor:])
            ast = {
                'type': 'function',
                'value': t['value'].strip(),
                'args': args,
            }
            cursor += 2

        break

    if cursor != len(tokens):
        raise Exception('Failed to parse node: ' + tokens[cursor]['value'])

    return ast


def parse_node_args(tokens):
    args = []
    cursor = 0
    while cursor < len(tokens):
        t = getelement(tokens, cursor)
        if t['value'] == ')':
            return args, cursor + 1
        
        if len(args) and t['value'] == ',':
            cursor += 1
        elif len(args) and t['value'] != ',':
            raise Exception('Expected comma to separate args')

        args.append(getelement(tokens, cursor))
        cursor += 1

    return args, cursor


def interpret(outfd, ast, env):
    for item in ast:
        item_type = item['type']
        node = item['value']

        if item_type == 'text':
            outfd.write(node['value'])
            continue

        if item_type == 'tag':
            tag_value = interpret_node(node, env)
            outfd.write(tag_value)
            continue

        if item_type == 'block':
            interpret_block(outfd, node, item['child'], env)
            continue

        raise Exception('Unknown type: ' + item_type)


def interpret_node(node, env):
    if node['type'] == 'literal':
        # Is a string
        if node['value'][0] == "'" and node['value'][-1] == "'":
            return node['value'][1:-1]

        # Default to an env lookup
        return env[node['value']]

    function = node['value']
    args = node['args']
    if function == '==':
        arg_vals = [interpret_node(arg) for arg in args]
        if arg_vals.count(arg_vals[0]) == len(arg_vals):
            return True

        return False

    if function == 'get':
        arg_vals = [interpret_node(arg, env) for arg in args]
        return arg_vals[0][arg_vals[1]]

    raise Exception('Unknown function: ' + function)


def interpret_block(outfd, node, child, env):
    function = node['value']
    args = node['args']
    if function == 'if' and interpret_node(node):
        interpret(outfd, child, env)
        return

    if function == 'for-in':
        loop_variable = args[1]
        loop_iter_variable = args[0]['value']

        for elem in interpret_node(loop_variable, env):
            child_env = env.copy()
            child_env[loop_iter_variable] = elem
            interpret(outfd, child, child_env)

        return

    raise Exception('Unsupported block node function: ' + function)
