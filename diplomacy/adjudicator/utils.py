from subprocess import Popen, PIPE, STDOUT
import affine
import os

def svg_to_png(svg: bytes, file_name: str):

    p = Popen(["inkscape", "--pipe", "--export-type=png"], stdout=PIPE, stdin=PIPE, stderr=PIPE)
    data = p.communicate(input=svg)[0]

    # Stupid inkscape error fix, not good but works
    # Inkscape can throw warnings in stdout, this should remove those warnings, leaving us with a valid png

    # This should indicate the start of the png, see https://www.w3.org/TR/2003/REC-PNG-20031110/#5PNG-file-signature
    png_start = b'\x89PNG\r\n\x1a\n'

    if data[:8] != png_start:
        data = data[data.find(png_start):]

        if data[:8] != png_start:
            raise RuntimeError("Something went wrong with making the png.")

    base = os.path.splitext(file_name)[0]
    return bytes(data), base + ".png"
