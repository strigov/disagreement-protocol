from app.services.party_extractor import ExtractedParty, PartyExtractor


def test_extracts_two_parties_with_role_labels():
    preamble = (
        'ООО "Ромашка", в лице директора Иванова И.И., именуемое в дальнейшем "Арендодатель", '
        'и АО "Василёк", в лице Петрова П.П., именуемое в дальнейшем "Арендатор", '
        "заключили настоящий договор"
    )
    parties = PartyExtractor().extract(preamble)
    assert len(parties) == 2
    by_role = {p.role: p for p in parties}
    assert "Арендодатель" in by_role
    assert "Арендатор" in by_role
    assert "Ромашка" in by_role["Арендодатель"].name
    assert "Василёк" in by_role["Арендатор"].name


def test_handles_far_form_dalee():
    preamble = (
        'ИП Сидоров А.А. (далее — Исполнитель) и ПАО "СберТех" (далее — Заказчик)'
    )
    parties = PartyExtractor().extract(preamble)
    roles = sorted(p.role for p in parties)
    assert roles == ["Заказчик", "Исполнитель"]
    by_role = {p.role: p for p in parties}
    assert by_role["Заказчик"].name == 'ПАО "СберТех"'


def test_returns_empty_for_text_without_parties():
    assert PartyExtractor().extract("Никаких сторон тут нет") == []
