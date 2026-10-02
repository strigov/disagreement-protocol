from copy import deepcopy

from app.models.document import Document
from app.models.party import Party
from app.models.protocol import Protocol
from app.schemas.protocol_form import ProtocolForm, ProtocolFormPatch, Signature
from app.services.protocol_generator import edition_label


CLOSING_TEXT = (
    "Во всем остальном, что не изменено настоящим протоколом разногласий, "
    "Стороны руководствуются условиями договора.\n"
    "Настоящий протокол является неотъемлемой частью договора. "
    "Изменения, изложенные в настоящем протоколе, применяются после его подписания обеими Сторонами.\n"
    "Настоящий протокол составлен в двух экземплярах, имеющих одинаковую юридическую силу, "
    "по одному для каждой из Сторон."
)


def resolve_form(protocol: Protocol, doc: Document, parties: list[Party]) -> ProtocolForm:
    drafting = next((p for p in parties if p.id == doc.drafting_party_id), None)
    other = next((p for p in parties if p.id != doc.drafting_party_id), None)
    # Stable party IDs keep signature details with their owner across side swaps.
    ordered = sorted(parties, key=lambda p: str(p.id))
    defaults = ProtocolForm(
        contract_reference=doc.contract_name or "",
        closing_text=CLOSING_TEXT,
        original_title=edition_label(other.role if other else "", "Стороны 1"),
        proposed_title=edition_label(drafting.role if drafting else "", "Стороны 2"),
        signatures={str(p.id): Signature(name=p.name, role=p.role) for p in ordered},
    ).model_dump()
    overrides = protocol.form_json or {}
    for key, value in overrides.items():
        if key != "signatures":
            defaults[key] = value
    for party_id, signature in overrides.get("signatures", {}).items():
        if party_id in defaults["signatures"]:
            defaults["signatures"][party_id].update(signature)
    if "opening_text" not in overrides:
        names = " и ".join(
            (signature["name"] or "__________________") + (f" ({signature['role']})" if signature["role"] else "")
            for signature in defaults["signatures"].values()
        )
        defaults["opening_text"] = (f"{names}, совместно именуемые «Стороны», " if names else "Стороны ") + (
            "договорились заключить договор с учетом настоящего протокола разногласий "
            "и изложить указанные ниже условия договора в согласованной редакции:"
        )
    return ProtocolForm.model_validate(defaults)


def apply_form_patch(protocol: Protocol, patch: ProtocolFormPatch) -> None:
    # Store only overrides: generated party labels continue to follow party edits.
    data = deepcopy(protocol.form_json or {})
    changes = patch.model_dump(mode="json", exclude_unset=True)
    for key, value in changes.items():
        if value is None:
            data.pop(key, None)
        elif key == "signatures":
            signatures = data.setdefault("signatures", {})
            for party_id, fields in value.items():
                signature = signatures.setdefault(party_id, {})
                for field, text in fields.items():
                    if text is None:
                        signature.pop(field, None)
                    else:
                        signature[field] = text
        else:
            data[key] = value
    protocol.form_json = data
