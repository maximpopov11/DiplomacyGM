import asyncio
from subprocess import PIPE
import os


async def svg_to_png(svg: bytes, file_name: str):
    # https://gitlab.com/inkscape/inkscape/-/issues/4716
    os_env = os.environ.copy()
    os_env["SELF_CALL"] = "xxx"
    p = await asyncio.create_subprocess_shell("inkscape --pipe --export-type=png --export-dpi=200", stdout=PIPE, stdin=PIPE, stderr=PIPE, env=os_env)
    data, error = await p.communicate(input=svg)

    # Stupid inkscape error fix, not good but works
    # Inkscape can throw warnings in stdout, this should remove those warnings, leaving us with a valid png

    # This should indicate the start of the png, see https://www.w3.org/TR/2003/REC-PNG-20031110/#5PNG-file-signature
    png_start = b'\x89PNG\r\n\x1a\n'

    if data[:8] != png_start:
        data = data[data.find(png_start):]

        if data[:8] != png_start:
            print(data)
            print(error)
            raise RuntimeError("Something went wrong with making the png.")

    base = os.path.splitext(file_name)[0]
    return bytes(data), base + ".png"
