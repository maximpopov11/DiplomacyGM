import asyncio
from subprocess import PIPE
import os

limit = os.getenv("simultaneous_svg_exports_limit")
if limit == None:
    limit = 4
external_task_limit = asyncio.Semaphore(int(limit))

async def svg_to_png(svg: bytes, file_name: str):
    async with external_task_limit:
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
                raise RuntimeError("Something went wrong with making the png.")

        base = os.path.splitext(file_name)[0]
        return bytes(data), base + ".png"


async def png_to_jpg(png: bytes, file_name: str) -> (bytes, str):
    async with external_task_limit:
        p = await asyncio.create_subprocess_shell("magick png:- jpg:-", stdout=PIPE,
                                                  stdin=PIPE, stderr=PIPE)
        data, error = await p.communicate(input=png)
        base = os.path.splitext(file_name)[0]
        return bytes(data), base + ".jpg"