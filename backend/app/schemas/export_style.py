from typing import Literal

from pydantic import BaseModel, Field


# Word's standard font colors and text-marker palette (OOXML w:highlight).
FontColor = Literal[
    "000000", "FFFFFF", "C00000", "FF0000", "FFC000", "FFFF00", "92D050",
    "00B050", "00B0F0", "0070C0", "002060", "7030A0",
]
HighlightColor = Literal[
    "yellow", "green", "cyan", "magenta", "blue", "red", "darkBlue",
    "darkCyan", "darkGreen", "darkMagenta", "darkRed", "darkYellow",
    "darkGray", "lightGray", "black",
]


class AdditionStyle(BaseModel):
    color: FontColor | None = "00B050"
    highlight: HighlightColor | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False


class DeletionStyle(AdditionStyle):
    color: FontColor | None = "FF0000"
    strike: bool = False


class ChangeHighlighting(BaseModel):
    enabled: bool = False
    deletions: DeletionStyle = Field(default_factory=DeletionStyle)
    additions: AdditionStyle = Field(default_factory=AdditionStyle)
