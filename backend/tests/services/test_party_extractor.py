import pytest

from app.services.party_extractor import PartyExtractor


def test_suppresses_representative_when_unknown_first_party_precedes_it():
    preamble = (
        'Город Москва, в лице ГУП «МГЦАЖ», именуемый в дальнейшем «Арендодатель», '
        'и ООО «Ромашка», именуемое в дальнейшем «Арендатор»'
    )

    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == [
        ('ООО «Ромашка»', "Арендатор"),
    ]


def test_accepts_documented_qualifier_before_entity_prefix():
    preamble = (
        'ЗАО «Америабанк», именуемое в дальнейшем «Продавец», в лице генерального директора '
        'Иванова И.И., действующего на основании Устава, и юридическое лицо ООО «Дискавери '
        'Ситипарк» (далее — Покупатель), в лице генерального директора Петрова П.П., '
        'действующего на основании Устава, совместно именуемые Стороны, а по отдельности '
        'Сторона, заключили настоящий договор о нижеследующем:'
    )

    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == [
        ('ЗАО «Америабанк»', "Продавец"),
        ('ООО «Дискавери Ситипарк»', "Покупатель"),
    ]


def test_ignores_organization_after_notarial_authority_basis():
    preamble = (
        'ООО «Альфа», в лице генерального директора Иванова И.И., действующего на основании '
        'доверенности от 01.02.2025, удостоверенной нотариусом города Москвы Петровой П.П., '
        'и Устава ООО «УК Прогресс», именуемое в дальнейшем «Арендодатель», с одной стороны, '
        'и ООО «Бета», именуемое в дальнейшем «Арендатор», с другой стороны'
    )

    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == [
        ('ООО «Альфа»', "Арендодатель"),
        ('ООО «Бета»', "Арендатор"),
    ]


def test_ignores_organization_after_multiple_authority_basis_items():
    preamble = (
        'ООО «Альфа», в лице директора, действующего на основании Устава, утверждённого '
        'решением единственного участника, и договора управления, заключённого с ООО '
        '«Управдом», именуемое в дальнейшем «Заказчик», и ООО «Бета», именуемое в дальнейшем '
        '«Исполнитель»'
    )

    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == [
        ('ООО «Альфа»', "Заказчик"),
        ('ООО «Бета»', "Исполнитель"),
    ]


def test_does_not_treat_authority_basis_union_as_party_separator():
    preamble = (
        'Общество с ограниченной ответственностью «Де Вижен», именуемое в дальнейшем '
        '«Лицензиар», в лице Генерального директора Иванова И.И., действующего на основании '
        'Устава и Решения единственного участника ООО «Де Вижен», с одной стороны, и любое '
        'физическое лицо, именуемое в дальнейшем «Лицензиат», с другой стороны'
    )

    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == [
        ('Общество с ограниченной ответственностью «Де Вижен»', "Лицензиар"),
    ]


def test_splits_next_party_after_in_face_when_union_follows_role():
    preamble = (
        'ООО «Альфа» (далее — Продавец), в лице директора Иванова И.И., '
        'и ООО «Бета», именуемое в дальнейшем «Покупатель»'
    )

    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == [
        ("ООО «Альфа»", "Продавец"),
        ("ООО «Бета»", "Покупатель"),
    ]


def test_ignores_organization_inside_v_litse_before_party_role():
    preamble = (
        'ООО "Альфа", в лице управляющей компании ООО «Управдом», '
        'именуемое в дальнейшем "Заказчик"'
    )

    parties = PartyExtractor().extract(preamble)

    assert len(parties) == 1
    assert parties[0].name == 'ООО "Альфа"'
    assert parties[0].role == "Заказчик"
    assert parties[0].confidence == 0.9


def test_releases_in_face_suppression_after_parenthetical_dash_role():
    preamble = (
        'ООО «Альфа», в лице директора Иванова И.И., действующего на основании Устава '
        '(далее — Заказчик), и ООО «Бета» (далее — Исполнитель)'
    )

    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == [
        ("ООО «Альфа»", "Заказчик"),
        ("ООО «Бета»", "Исполнитель"),
    ]


def test_releases_in_face_suppression_for_mixed_role_forms():
    preamble = (
        'ООО «Альфа», в лице директора Иванова И.И., действующего на основании Устава '
        '(далее — Продавец), и ООО «Бета», именуемое в дальнейшем «Покупатель»'
    )

    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == [
        ("ООО «Альфа»", "Продавец"),
        ("ООО «Бета»", "Покупатель"),
    ]


def test_reversed_role_marker_does_not_return_wrong_first_party():
    preamble = (
        'ООО «Альфа», в лице директора Иванова И.И., действующего на основании Устава, '
        'в дальнейшем именуемое «Заказчик», и ООО «Бета», '
        'именуемое в дальнейшем «Исполнитель»'
    )

    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == [
        ("ООО «Бета»", "Исполнитель"),
    ]


@pytest.mark.parametrize(
    ("preamble", "expected"),
    [
        (
            'ООО «Альфа», именуемое в дальнейшем «Заказчик», и ООО «Бета», '
            'в лице управляющей компании ООО «Управдом», именуемое в дальнейшем '
            '«Исполнитель»',
            [("ООО «Альфа»", "Заказчик"), ("ООО «Бета»", "Исполнитель")],
        ),
        (
            'ООО «Альфа», в лице управляющей компании ООО «Управдом», именуемое '
            'в дальнейшем «Заказчик», и ООО «Бета», в лице управляющей компании '
            'ООО «Управдом», именуемое в дальнейшем «Исполнитель»',
            [("ООО «Альфа»", "Заказчик"), ("ООО «Бета»", "Исполнитель")],
        ),
        (
            'ООО «Альфа», именуемое в дальнейшем «Заказчик», и ООО «Бета», '
            'в лице управляющей компании ООО «Управдом», именуемое в дальнейшем '
            '«Исполнитель», и ООО «Гамма», именуемое в дальнейшем «Покупатель»',
            [
                ("ООО «Альфа»", "Заказчик"),
                ("ООО «Бета»", "Исполнитель"),
                ("ООО «Гамма»", "Покупатель"),
            ],
        ),
        (
            'ООО "Альфа",\nв лице управляющей компании ООО «Управдом»,\n'
            'именуемое в дальнейшем "Заказчик",\nи ООО «Бета»,\n'
            'именуемое в дальнейшем «Исполнитель»',
            [("ООО \"Альфа\"", "Заказчик"), ("ООО «Бета»", "Исполнитель")],
        ),
        (
            'ООО "Альфа",\nВ  лице управляющей компании ООО\u00a0«Управдом»,\n'
            'именуемое в дальнейшем "Заказчик", и ООО «Бета», '
            'именуемое в дальнейшем «Исполнитель»',
            [("ООО \"Альфа\"", "Заказчик"), ("ООО «Бета»", "Исполнитель")],
        ),
    ],
)
def test_in_face_boundary_regressions(preamble, expected):
    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == expected


def test_in_face_marker_accepts_nbsp_between_words():
    preamble = (
        'ООО «Альфа», В\u00a0лице генерального директора Иванова И.И., '
        'именуемое в дальнейшем «Заказчик»'
    )

    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == [
        ("ООО «Альфа»", "Заказчик"),
    ]


@pytest.mark.parametrize(
    ("preamble", "expected"),
    [
        (
            'ООО «Альфа», в лице управляющей компании ООО «Управдом», '
            'именуемое в дальнейшем «Заказчик»',
            [("ООО «Альфа»", "Заказчик")],
        ),
        (
            'ООО «Альфа», в лице генерального директора Иванова И.И., '
            'именуемое в дальнейшем «Заказчик»',
            [("ООО «Альфа»", "Заказчик")],
        ),
        (
            'ООО «Альфа», именуемое в дальнейшем «Заказчик», и ООО «Бета», '
            'именуемое в дальнейшем «Исполнитель»',
            [("ООО «Альфа»", "Заказчик"), ("ООО «Бета»", "Исполнитель")],
        ),
        (
            'ООО «Группа «Ромашка» Холдинг», именуемое в дальнейшем «Заказчик»',
            [("ООО «Группа «Ромашка» Холдинг»", "Заказчик")],
        ),
    ],
)
def test_required_party_extraction_regressions(preamble, expected):
    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == expected


def test_party_with_in_face_clause_first_keeps_following_party():
    preamble = (
        'ООО "Альфа", в лице управляющей компании ООО «Управдом», '
        'именуемое в дальнейшем "Заказчик", и ООО «Бета», '
        'именуемое в дальнейшем «Исполнитель»'
    )

    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == [
        ('ООО "Альфа"', "Заказчик"),
        ('ООО «Бета»', "Исполнитель"),
    ]


def test_preserves_one_nested_guillemet_level_in_party_name():
    preamble = (
        'ООО «Группа «Ромашка» Холдинг», именуемое в дальнейшем «Заказчик»'
    )

    parties = PartyExtractor().extract(preamble)

    assert len(parties) == 1
    assert parties[0].name == 'ООО «Группа «Ромашка» Холдинг»'
    assert parties[0].role == "Заказчик"
    assert parties[0].confidence == 0.9


def test_nested_guillemet_does_not_consume_following_party():
    preamble = (
        'ООО «Группа «Ромашка» Холдинг», именуемое в дальнейшем «Заказчик», '
        'и АО «Дельта», именуемое в дальнейшем «Арендатор»'
    )

    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == [
        ('ООО «Группа «Ромашка» Холдинг»', "Заказчик"),
        ('АО «Дельта»', "Арендатор"),
    ]


def test_extracts_sample_03_parties_with_full_legal_forms_and_guillemets():
    preamble = (
        "Общество с ограниченной ответственностью «Гамма», в лице генерального директора "
        "Смирнова А.В., действующего на основании Устава, именуемое в дальнейшем "
        "«Арендодатель», с одной стороны, и Акционерное общество «Дельта», в лице "
        "коммерческого директора Волкова В.В., именуемое в дальнейшем «Арендатор», "
        "с другой стороны, заключили настоящий Договор о нижеследующем."
    )

    parties = PartyExtractor().extract(preamble)

    assert len(parties) == 2
    assert [(party.name, party.role) for party in parties] == [
        ("Общество с ограниченной ответственностью «Гамма»", "Арендодатель"),
        ("Акционерное общество «Дельта»", "Арендатор"),
    ]


@pytest.mark.parametrize(
    ("opening", "closing"),
    [("„", "“"), ("“", "”"), ("”", "”")],
)
def test_accepts_curly_quote_variants_for_names_and_roles(opening, closing):
    preamble = (
        f"ООО {opening}Гамма{closing}, именуемое в дальнейшем {opening}Арендодатель{closing}"
    )

    parties = PartyExtractor().extract(preamble)

    assert [(party.name, party.role) for party in parties] == [
        (f"ООО {opening}Гамма{closing}", "Арендодатель"),
    ]


def test_extracts_full_individual_entrepreneur_in_dash_form():
    preamble = "Индивидуальный предприниматель Сидоров А.А. (далее — Исполнитель)"

    parties = PartyExtractor().extract(preamble)

    assert len(parties) == 1
    assert parties[0].name == "Индивидуальный предприниматель Сидоров А.А."
    assert parties[0].role == "Исполнитель"


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
