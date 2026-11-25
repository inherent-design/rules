"""Read class/member locators from official ProGuard-format mappings.

These locators do not establish behavior or transformation equivalence.
"""
import re


def read(path):
    classes = {}
    current = None
    for line in path.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        header = re.fullmatch(r"(\S+) -> (\S+):", line)
        if header:
            current = {"name": header[2], "fields": {}, "methods": {}, "ambiguousMethods": {}}
            classes[header[1]] = current
            continue
        if current is None or " -> " not in line:
            continue
        left, target = line.strip().rsplit(" -> ", 1)
        method = re.search(r"([^\s:]+\([^)]*\))$", left)
        if method:
            signature = method[1]
            # A return-qualified locator distinguishes covariant bridge methods.
            return_type = re.sub(r"^(?:\d+:\d+:)?", "", left[:method.start()].strip())
            current["methods"][return_type + " " + signature] = target
            ambiguous = current["ambiguousMethods"]
            previous = current["methods"].get(signature)
            if signature in ambiguous:
                ambiguous[signature] = sorted(set(ambiguous[signature] + [target]))
            elif previous is not None and previous != target:
                # Covariant/bridge methods can share arguments but differ in
                # return type and bytecode name. Never silently select one.
                ambiguous[signature] = sorted({previous, target})
                del current["methods"][signature]
            else:
                current["methods"][signature] = target
        elif "(" not in left:
            parts = left.split()
            if len(parts) != 2:
                raise ValueError(f"Unsupported mapped field: {left}")
            current["fields"][parts[1]] = target
    return classes
