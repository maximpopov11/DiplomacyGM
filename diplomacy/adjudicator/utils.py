from resvg import render, usvg
import affine
import os

def svg_to_png(svg: bytes, file_name: str):
    db = usvg.FontDatabase.default()
    db.load_system_fonts()

    options = usvg.Options.default()

    tree = usvg.Tree.from_str(svg.decode(), options, db)
    scale = 2
    (w, h) = tree.int_size()
    target_size = (w*scale, h*scale)

    tr = affine.Affine.scale(scale)
    data = render(tree, tr[0:6], bg_size=target_size)

    base = os.path.splitext(file_name)[0]

    return bytes(data), base + ".png"