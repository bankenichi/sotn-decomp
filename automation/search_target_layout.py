"""Bounded named memory views derived solely from archived US C declarations."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys
import tempfile


# Include every executable parser dependency, including the generated tables.
# Neither a host-installed parser nor m2c's implicit typedefs are ABI evidence.
LAYOUT_DEPENDENCIES = (
    "automation/search_target_layout.py",
    "tools/m2c/m2c/__init__.py", "tools/m2c/m2c/c_types.py", "tools/m2c/m2c/error.py",
    *("tools/m2c/m2c_pycparser/" + name + ".py" for name in (
        "__init__", "c_ast", "c_generator", "c_parser", "c_lexer", "plyparser",
        "ast_transforms", "lextab", "yacctab", "ply/__init__", "ply/lex", "ply/yacc")),
)
RENDERER_DEPENDENCIES = (
    "automation/search_target_renderer.py", "automation/search_source_context.py",
    *LAYOUT_DEPENDENCIES,
)


def _parser():
    root = Path(__file__).resolve().parents[1] / "tools/m2c"
    for name, path in (("m2c_pycparser", root / "m2c_pycparser/__init__.py"),
                       ("_sotn_layout_m2c", root / "m2c/__init__.py")):
        loaded = sys.modules.get(name)
        if loaded is not None:
            if Path(loaded.__file__).resolve() != path.resolve():
                raise ValueError("layout parser was loaded from a different dependency")
            continue
        spec = importlib.util.spec_from_file_location(name, path, submodule_search_locations=[str(path.parent)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    from _sotn_layout_m2c import c_types
    return c_types


def renderer_type_declarations(context: bytes) -> str:
    """Keep the US types needed by standalone seeds, excluding game definitions."""
    ct = _parser()
    ast, _ = ct.parse_c(ct.strip_comments(context.decode("utf-8")), None)
    declarations = []
    for item in ast.ext:
        if isinstance(item, ct.ca.Pragma):
            declarations.append(ct.to_c(item))
        elif isinstance(item, ct.ca.Typedef) or isinstance(item, ct.ca.Decl) and item.name is None:
            declarations.append(ct.to_c(item) + ";")
    return "\n".join(declarations) + "\n"


def pointer_layouts(context: bytes, kinds) -> dict:
    """Project integral pointees and named members with US 32-bit ABI offsets.

    No cache pickle is read or written. Parsing the exact context first rejects
    types that m2c would otherwise invent via its decompiler convenience aliases.
    Layout failure is a real unsupported context, not a fabricated memory view.
    """
    kinds = sorted(set(kinds))
    if not kinds:
        return {}
    if len(context) > 8 * 1024 * 1024 or len(kinds) > 64:
        raise ValueError("target layout input exceeds bound")
    ct = _parser()
    ca = ct.ca
    try:
        text = context.decode("utf-8")
        exact_ast, exact_scope = ct.parse_c(ct.strip_comments(text), None)
        exact_typedefs = {item.name: item.type for item in exact_ast.ext if isinstance(item, ca.Typedef)}
        with tempfile.TemporaryDirectory(prefix="us-layout-") as directory:
            path = Path(directory) / "context.c"
            path.write_text(text, encoding="utf-8")
            typemap = ct.build_typemap([path], ct.ArchC(), use_cache=False)
    except (ct.DecompFailure, ValueError, AssertionError, RecursionError):
        return {}

    def resolve(node):
        quals = set()
        for _ in range(32):
            quals.update(getattr(node, "quals", ()))
            if (isinstance(node, ca.TypeDecl) and isinstance(node.type, ca.IdentifierType)
                    and len(node.type.names) == 1 and node.type.names[0] in exact_typedefs):
                node = exact_typedefs[node.type.names[0]]
            else:
                return node, quals
        raise ValueError("recursive typedef")

    def leaves(node, offset, path, writable, depth, output):
        if depth > 8 or len(output) >= 512:
            raise ValueError("target layout expansion limit")
        node, quals = resolve(node)
        writable = writable and "const" not in quals
        if isinstance(node, ca.ArrayDecl):
            if node.dim is None:
                raise ValueError("flexible array has no bounded layout")
            count = ct.parse_constant_int(node.dim, typemap)
            size, _, _ = ct.parse_struct_member(node.type, "", typemap, allow_unsized=False)
            if not 0 < count <= 128:
                raise ValueError("array layout exceeds bound")
            for index in range(count):
                leaves(node.type, offset + index * size, path + "[" + str(index) + "]", writable, depth + 1, output)
        elif isinstance(node, ca.TypeDecl) and isinstance(node.type, (ca.Struct, ca.Union)):
            struct = ct.parse_struct(node.type, typemap)
            if struct.has_bitfields:
                # Entity contains an unnamed full-width padding bitfield. Its
                # extent is endian-independent; partial/named bitfields are not.
                for declaration in node.type.decls or ():
                    if getattr(declaration, "bitsize", None) is not None:
                        width = ct.parse_constant_int(declaration.bitsize, typemap)
                        size, _, _ = ct.parse_struct_member(declaration.type, "", typemap, allow_unsized=False)
                        if declaration.name is not None or width != size * 8:
                            raise ValueError("bitfield layout requires target-specific evidence")
            for start, fields in sorted(struct.fields.items()):
                for field in fields:
                    if not field.name or not re.fullmatch(r"[A-Za-z_]\w*", field.name):
                        raise ValueError("unnamed memory member")
                    checkpoint = len(output)
                    try:
                        leaves(field.type, offset + start, path + "." + field.name, writable, depth + 1, output)
                    except ValueError:
                        del output[checkpoint:]
                        if isinstance(node.type, ca.Union):
                            raise
                        # Unsupported nested members do not erase proven fields
                        # elsewhere in a struct. A union must retain all choices.
                        continue
        elif isinstance(node, ca.TypeDecl) and isinstance(node.type, ca.IdentifierType):
            names = node.type.names
            if not set(names) <= {"signed", "unsigned", "char", "short", "int", "long"}:
                return
            width = ct.primitive_size(node.type)
            if width in {1, 2, 4}:
                output.append({"offset": offset, "width": width, "signed": "unsigned" not in names,
                               "path": path, "writable": writable})
        # Pointer-valued, floating, enum and aggregate accesses are not lowered.

    result = {}
    for kind in kinds:
        if not re.fullmatch(r"[A-Za-z_]\w*(?: [A-Za-z_]\w*)*\**", kind):
            continue
        try:
            ast, _ = ct.parse_c(kind + " __sotn_layout_value;", exact_scope)
            pointer, _ = resolve(ast.ext[0].type)
            if not isinstance(pointer, ca.PtrDecl):
                continue
            pointee, _ = resolve(pointer.type)
            size, align, _ = ct.parse_struct_member(pointer.type, "", typemap, allow_unsized=False)
            if not 0 < size <= 65536 or align <= 0:
                continue
            members = []
            leaves(pointer.type, 0, "", True, 0, members)
            if members:
                result[kind] = {"size": size, "align": align, "scalar": isinstance(pointee, ca.TypeDecl)
                                and isinstance(pointee.type, ca.IdentifierType), "members": members}
        except (ct.DecompFailure, ValueError, AssertionError, RecursionError):
            continue
    return result
