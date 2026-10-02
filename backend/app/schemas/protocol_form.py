"""Editable document framing. Null in a PATCH restores the generated default."""
import re
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def xml_text(value: str) -> str:
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]", value):
        raise ValueError("Текст содержит недопустимые для DOCX символы")
    return value


ShortText = Annotated[str, Field(strict=True, max_length=500), AfterValidator(xml_text)]
BodyText = Annotated[str, Field(strict=True, max_length=20000), AfterValidator(xml_text)]
def nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("Название не должно быть пустым")
    return value.strip()


Heading = Annotated[ShortText, AfterValidator(nonblank)]


class Signature(BaseModel):
    name: ShortText = ""
    role: ShortText = ""
    position: ShortText = ""
    full_name: ShortText = ""


class SignaturePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: ShortText | None = None
    role: ShortText | None = None
    position: ShortText | None = None
    full_name: ShortText | None = None


class ProtocolForm(BaseModel):
    title: Heading = "Протокол разногласий"
    contract_reference: ShortText = ""
    place: ShortText = ""
    date: ShortText = ""
    opening_text: BodyText = ""
    closing_text: BodyText = ""
    point_title: Heading = "Пункт договора"
    original_title: Heading = "Редакция Стороны 1"
    proposed_title: Heading = "Редакция Стороны 2"
    agreed_title: Heading = "Согласованная редакция"
    mark_drafting_signature: bool = True
    signatures: dict[str, Signature] = Field(default_factory=dict)


class ProtocolFormPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Heading | None = None
    contract_reference: ShortText | None = None
    place: ShortText | None = None
    date: ShortText | None = None
    opening_text: BodyText | None = None
    closing_text: BodyText | None = None
    point_title: Heading | None = None
    original_title: Heading | None = None
    proposed_title: Heading | None = None
    agreed_title: Heading | None = None
    mark_drafting_signature: bool | None = None
    signatures: dict[UUID, SignaturePatch] | None = Field(default=None, max_length=2)
