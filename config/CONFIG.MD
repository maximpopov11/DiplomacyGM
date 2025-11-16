# CONFIG FORMAT
The config format is fairly simple
It specifies how the bot should read your svg
It is a .json file (see the two examples), which contains various named values that can be set

## NAME & FILE
The "name" element is the name of your variant.
The "file" element is the relative path of your svg


## SVG CONFIG
The SVG config is still a work in progress.
The "layer" that it is referring to is the internal name of the inscape layer
You can find the it in the SVG file. If you are using Inkscape, you will likely find id="..." next to
inkscape:groupmode="layer" and inkscape:label="...", the latter of which may describe which of the following (if any)
the group represents. You are looking for the text in the id="..."

Individual explanations of the layers coming at some point in the future


## OVERRIDES
The overrides are used to manually set aspects of the svg that the bot can't read correctly (i. e. multiple coasts)
