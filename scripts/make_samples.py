"""Генератор тестовых .docx для ручной и сквозной проверки пайплайна.

Запуск (из backend-окружения, нужен только lxml/стандартная библиотека):

    cd backend && uv run python ../scripts/make_samples.py

Файлы складываются в ../samples/. Каждый документ собирается как настоящий
OOXML-пакет, поэтому Track Changes (w:ins / w:del / w:rPrChange), автонумерация
Word (numbering.xml) и стилевая нумерация (styles.xml) присутствуют в том виде,
в каком их пишет Word, а не эмулируются.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
DATE = "2026-07-01T10:00:00Z"

OUT = Path(__file__).resolve().parent.parent / "samples"

_rev_id = [1000]


def rid() -> int:
    _rev_id[0] += 1
    return _rev_id[0]


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --- run-уровень -----------------------------------------------------------


def run(text: str, bold: bool = False, italic: bool = False) -> str:
    rpr = ""
    if bold or italic:
        rpr = f"<w:rPr>{'<w:b/>' if bold else ''}{'<w:i/>' if italic else ''}</w:rPr>"
    return f'<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def ins(text: str, author: str = "Юрист контрагента") -> str:
    return (
        f'<w:ins w:id="{rid()}" w:author="{author}" w:date="{DATE}">'
        f'{run(text)}</w:ins>'
    )


def dele(text: str, author: str = "Юрист контрагента") -> str:
    return (
        f'<w:del w:id="{rid()}" w:author="{author}" w:date="{DATE}">'
        f'<w:r><w:delText xml:space="preserve">{esc(text)}</w:delText></w:r></w:del>'
    )


def format_only(text: str, author: str = "Юрист контрагента") -> str:
    """Правка только форматирования: текст не меняется, меняется w:rPr."""
    return (
        f"<w:r><w:rPr><w:b/>"
        f'<w:rPrChange w:id="{rid()}" w:author="{author}" w:date="{DATE}">'
        f"<w:rPr/></w:rPrChange></w:rPr>"
        f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'
    )


# --- параграфы -------------------------------------------------------------


def ppr(num_id: int | None = None, ilvl: int | None = None, style: str | None = None,
        para_mark: str | None = None) -> str:
    parts = []
    if style:
        parts.append(f'<w:pStyle w:val="{style}"/>')
    if num_id is not None:
        parts.append(
            f'<w:numPr><w:ilvl w:val="{ilvl or 0}"/><w:numId w:val="{num_id}"/></w:numPr>'
        )
    if para_mark in ("ins", "del"):
        parts.append(
            f'<w:rPr><w:{para_mark} w:id="{rid()}" w:author="Юрист контрагента" '
            f'w:date="{DATE}"/></w:rPr>'
        )
    return f"<w:pPr>{''.join(parts)}</w:pPr>" if parts else ""


def para(content: str, num_id: int | None = None, ilvl: int | None = None,
         style: str | None = None, para_mark: str | None = None) -> str:
    return f"<w:p>{ppr(num_id, ilvl, style, para_mark)}{content}</w:p>"


def text_para(text: str, **kw) -> str:
    return para(run(text), **kw)


# --- таблицы ---------------------------------------------------------------


def cell(content: str, width: int = 3000) -> str:
    return (
        f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/></w:tcPr>'
        f"<w:p>{content}</w:p></w:tc>"
    )


def table(rows: list[list[str]]) -> str:
    """rows — список строк, каждая ячейка уже отрендеренный run-контент."""
    body = "".join("<w:tr>" + "".join(cell(c) for c in row) + "</w:tr>" for row in rows)
    return (
        "<w:tbl><w:tblPr><w:tblBorders>"
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        "</w:tblBorders></w:tblPr>" + body + "</w:tbl>"
    )


# --- сборка пакета ---------------------------------------------------------

CONTENT_TYPES_HEAD = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Default Extension="bin" ContentType="application/vnd.ms-office.vbaProject"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
)

ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    f'<Relationship Id="rId1" Type="{R}/officeDocument" Target="word/document.xml"/>'
    "</Relationships>"
)

STYLES_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W}">
  <w:docDefaults>
    <w:rPrDefault><w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
      <w:sz w:val="24"/>
    </w:rPr></w:rPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="ContractHeading">
    <w:name w:val="Contract Heading"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:numPr><w:ilvl w:val="0"/><w:numId w:val="3"/></w:numPr>
    </w:pPr>
    <w:rPr><w:b/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="ContractHeadingBold">
    <w:name w:val="Contract Heading Bold"/>
    <w:basedOn w:val="ContractHeading"/>
    <w:rPr><w:b/><w:caps/></w:rPr>
  </w:style>
</w:styles>"""


def numbering_xml(*, with_overrides: bool = False, with_style_num: bool = False) -> str:
    abstracts = [
        # 0 — классическая договорная нумерация 1. / 1.1. / 1.1.1.
        """<w:abstractNum w:abstractNumId="0">
             <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
             <w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1.%2."/></w:lvl>
             <w:lvl w:ilvl="2"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1.%2.%3."/></w:lvl>
           </w:abstractNum>"""
    ]
    nums = ['<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>']

    if with_overrides:
        # 1 — нумерация приложения, стартует с 1 через startOverride
        abstracts.append(
            """<w:abstractNum w:abstractNumId="1">
                 <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
                 <w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1.%2."/></w:lvl>
               </w:abstractNum>"""
        )
        nums.append(
            """<w:num w:numId="2"><w:abstractNumId w:val="1"/>
                 <w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride>
               </w:num>"""
        )
    if with_style_num:
        # 2 — нумерация римскими для стиля ContractHeading
        abstracts.append(
            """<w:abstractNum w:abstractNumId="2">
                 <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="upperRoman"/><w:lvlText w:val="Статья %1."/></w:lvl>
               </w:abstractNum>"""
        )
        nums.append('<w:num w:numId="3"><w:abstractNumId w:val="2"/></w:num>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:numbering xmlns:w="{W}">' + "".join(abstracts) + "".join(nums) + "</w:numbering>"
    )


def build_docx(
    path: Path,
    body: str,
    *,
    numbering: str | None = None,
    styles: str | None = None,
    with_macros: bool = False,
) -> Path:
    doc_rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    overrides = []
    if numbering:
        doc_rels.append(f'<Relationship Id="rId10" Type="{R}/numbering" Target="numbering.xml"/>')
        overrides.append(
            '<Override PartName="/word/numbering.xml" ContentType='
            '"application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
        )
    if styles:
        doc_rels.append(f'<Relationship Id="rId11" Type="{R}/styles" Target="styles.xml"/>')
        overrides.append(
            '<Override PartName="/word/styles.xml" ContentType='
            '"application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        )
    doc_rels.append("</Relationships>")

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W}"><w:body>{body}'
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>'
        "</w:body></w:document>"
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES_HEAD + "".join(overrides) + "</Types>")
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("word/_rels/document.xml.rels", "".join(doc_rels))
        z.writestr("word/document.xml", document_xml)
        if numbering:
            z.writestr("word/numbering.xml", numbering)
        if styles:
            z.writestr("word/styles.xml", styles)
        if with_macros:
            z.writestr("word/vbaProject.bin", b"\x00\x01MACRO-PLACEHOLDER")
    return path


# ---------------------------------------------------------------------------
# 1. Простой договор: ручная нумерация в тексте, 3 правки
# ---------------------------------------------------------------------------


def sample_simple() -> Path:
    body = "".join([
        text_para("ДОГОВОР ПОСТАВКИ № 17/2026"),
        text_para("г. Москва                                        01 июля 2026 г."),
        text_para(
            'ООО "Ромашка", в лице генерального директора Иванова И.И., действующего на '
            'основании Устава, именуемое в дальнейшем "Поставщик", с одной стороны, и '
            'ООО "Василёк", в лице директора Петрова П.П., действующего на основании Устава, '
            'именуемое в дальнейшем "Покупатель", с другой стороны, заключили настоящий '
            "Договор о нижеследующем."
        ),
        text_para("1. Предмет договора"),
        # вставка внутри пункта
        para(
            run("1.1. Поставщик обязуется поставить Покупателю товар ")
            + ins("надлежащего качества ")
            + run("в количестве и ассортименте согласно спецификации.")
        ),
        text_para("1.2. Право собственности на товар переходит к Покупателю с момента подписания накладной."),
        text_para("2. Цена и порядок расчётов"),
        # удаление фрагмента
        para(
            run("2.1. Оплата производится в течение ")
            + dele("30 (тридцати)")
            + ins("10 (десяти)")
            + run(" банковских дней с момента поставки.")
        ),
        text_para("2.2. Цена товара включает НДС 20%."),
        text_para("3. Ответственность сторон"),
        para(
            run("3.1. За просрочку поставки Поставщик уплачивает пеню в размере ")
            + dele("0,1%")
            + ins("0,05%")
            + run(" от стоимости непоставленного товара за каждый день просрочки.")
        ),
        text_para("Реквизиты сторон"),
        text_para('Поставщик: ООО "Ромашка", ИНН 7701234567, р/с 40702810000000000001'),
        text_para('Покупатель: ООО "Василёк", ИНН 7707654321, р/с 40702810000000000002'),
    ])
    return build_docx(OUT / "01_simple_manual_numbering.docx", body)


# ---------------------------------------------------------------------------
# 2. Средний: автонумерация Word, новый и удалённый пункты, таблица
# ---------------------------------------------------------------------------


def sample_medium() -> Path:
    body = "".join([
        text_para("ДОГОВОР ОКАЗАНИЯ УСЛУГ № 42"),
        text_para(
            'ООО "Альфа", именуемое в дальнейшем "Заказчик", в лице директора Сидорова С.С., '
            'и ООО "Бета", именуемое в дальнейшем "Исполнитель", в лице директора Кузнецова К.К., '
            "заключили настоящий Договор о нижеследующем."
        ),
        # 1.
        text_para("Предмет договора", num_id=1, ilvl=0),
        # 1.1 — вставка
        para(
            run("Исполнитель обязуется оказать услуги по разработке программного обеспечения ")
            + ins("в соответствии с техническим заданием (Приложение № 1) "),
            num_id=1, ilvl=1,
        ),
        # 1.2 — без правок
        text_para("Заказчик обязуется принять и оплатить оказанные услуги.", num_id=1, ilvl=1),
        # 1.3 — новый пункт целиком
        para(
            ins("Исполнитель вправе привлекать соисполнителей с письменного согласия Заказчика."),
            num_id=1, ilvl=1, para_mark="ins",
        ),
        # 2.
        text_para("Стоимость услуг и порядок расчётов", num_id=1, ilvl=0),
        # 2.1 — замена суммы
        para(
            run("Стоимость услуг составляет ")
            + dele("1 000 000 (один миллион) рублей")
            + ins("850 000 (восемьсот пятьдесят тысяч) рублей")
            + run(", НДС не облагается."),
            num_id=1, ilvl=1,
        ),
        # 2.2 — удалённый пункт целиком
        para(
            dele("Заказчик перечисляет аванс в размере 50% от стоимости услуг."),
            num_id=1, ilvl=1, para_mark="del",
        ),
        # 2.3
        text_para("Окончательный расчёт производится по факту подписания акта.", num_id=1, ilvl=1),
        # 3.
        text_para("Сроки оказания услуг", num_id=1, ilvl=0),
        text_para("Услуги оказываются в сроки, указанные в таблице ниже.", num_id=1, ilvl=1),
        table([
            [run("Этап", bold=True), run("Срок", bold=True), run("Стоимость", bold=True)],
            [run("Проектирование"), run("15 рабочих дней"), run("200 000 руб.")],
            [run("Разработка"), run("40 рабочих дней"), run("500 000 руб.")],
            [run("Тестирование"), run("10 рабочих дней"), run("150 000 руб.")],
        ]),
        text_para("Реквизиты сторон"),
        text_para('Заказчик: ООО "Альфа", ИНН 7712345678'),
        text_para('Исполнитель: ООО "Бета", ИНН 7787654321'),
    ])
    return build_docx(OUT / "02_medium_auto_numbering.docx", body, numbering=numbering_xml())


# ---------------------------------------------------------------------------
# 3. Сложный: стилевая нумерация, приложение, таблица с правками,
#    format-only правка, вложенный ins в del, sdt-обёртка, кавычки-ёлочки
# ---------------------------------------------------------------------------


def sample_complex() -> Path:
    sdt_para = (
        "<w:sdt><w:sdtPr/><w:sdtContent>"
        + text_para(
            "Настоящий Договор составлен в двух экземплярах, имеющих равную юридическую силу."
        )
        + "</w:sdtContent></w:sdt>"
    )
    body = "".join([
        text_para("ДОГОВОР АРЕНДЫ НЕЖИЛОГО ПОМЕЩЕНИЯ № 8/АР"),
        text_para(
            "Общество с ограниченной ответственностью «Гамма», в лице генерального директора "
            "Смирнова А.В., действующего на основании Устава, именуемое в дальнейшем "
            "«Арендодатель», с одной стороны, и Акционерное общество «Дельта», в лице "
            "коммерческого директора Волкова В.В., именуемое в дальнейшем «Арендатор», "
            "с другой стороны, заключили настоящий Договор о нижеследующем."
        ),
        # Стилевая нумерация (numPr приходит из styles.xml через basedOn)
        text_para("ПРЕДМЕТ ДОГОВОРА", style="ContractHeadingBold"),
        para(
            run("Арендодатель передаёт, а Арендатор принимает во временное владение и пользование "
                "нежилое помещение общей площадью ")
            + dele("150 кв. м")
            + ins("175 кв. м")
            + run(", расположенное по адресу: г. Москва, ул. Ленина, д. 1."),
            num_id=1, ilvl=1,
        ),
        # format-only: текст не менялся, менялось только форматирование
        para(
            run("Помещение передаётся ")
            + format_only("в состоянии, пригодном для использования по назначению")
            + run("."),
            num_id=1, ilvl=1,
        ),
        # вложенная правка: внутри удалённого фрагмента другой автор вставил текст
        para(
            run("Срок аренды составляет ")
            + f'<w:del w:id="{rid()}" w:author="Юрист арендатора" w:date="{DATE}">'
            + f'<w:ins w:id="{rid()}" w:author="Юрист арендодателя" w:date="{DATE}">'
            + '<w:r><w:delText xml:space="preserve">11 (одиннадцать) месяцев</w:delText></w:r>'
            + "</w:ins></w:del>"
            + ins("3 (три) года с правом пролонгации")
            + run("."),
            num_id=1, ilvl=1,
        ),
        text_para("АРЕНДНАЯ ПЛАТА", style="ContractHeading"),
        para(
            run("Размер арендной платы указан в таблице:"),
            num_id=1, ilvl=1,
        ),
        # таблица с правкой внутри ячейки
        table([
            [run("Период", bold=True), run("Ставка, руб./кв. м", bold=True), run("Итого, руб.", bold=True)],
            [run("2026 год"), dele("1 200") + ins("1 100"), run("192 500")],
            [run("2027 год"), run("1 300"), run("227 500")],
        ]),
        # третий уровень нумерации
        text_para("Арендная плата перечисляется не позднее 5-го числа каждого месяца.",
                  num_id=1, ilvl=2),
        text_para("ПРОЧИЕ УСЛОВИЯ", style="ContractHeading"),
        sdt_para,
        para(
            ins("Все споры по настоящему Договору подлежат рассмотрению в Арбитражном суде "
                "города Москвы."),
            num_id=1, ilvl=1, para_mark="ins",
        ),
        # Приложение с собственной нумерацией (numId=2, startOverride)
        text_para("Приложение № 1"),
        text_para("Перечень передаваемого оборудования", num_id=2, ilvl=0),
        para(
            run("Кондиционер настенный — ")
            + dele("2 шт.")
            + ins("4 шт."),
            num_id=2, ilvl=1,
        ),
        text_para("Стеллаж металлический — 6 шт.", num_id=2, ilvl=1),
        text_para("Реквизиты сторон"),
        table([
            [run("Арендодатель", bold=True), run("Арендатор", bold=True)],
            [run("ООО «Гамма»\nИНН 7701111111"), run("АО «Дельта»\nИНН 7702222222")],
        ]),
    ])
    return build_docx(
        OUT / "03_complex_styles_annex_tables.docx",
        body,
        numbering=numbering_xml(with_overrides=True, with_style_num=True),
        styles=STYLES_XML,
    )


# ---------------------------------------------------------------------------
# 4. Крайние случаи
# ---------------------------------------------------------------------------


def sample_clean() -> Path:
    """Договор вообще без правок — протокол должен получиться пустым."""
    body = "".join([
        text_para("ДОГОВОР ХРАНЕНИЯ № 3"),
        text_para(
            'ООО "Эпсилон", именуемое в дальнейшем "Поклажедатель", и '
            'ООО "Дзета", именуемое в дальнейшем "Хранитель", заключили настоящий Договор.'
        ),
        text_para("Предмет договора", num_id=1, ilvl=0),
        text_para("Хранитель обязуется хранить переданное имущество.", num_id=1, ilvl=1),
        text_para("Поклажедатель обязуется оплатить услуги хранения.", num_id=1, ilvl=1),
    ])
    return build_docx(OUT / "04_edge_no_revisions.docx", body, numbering=numbering_xml())


def sample_macros() -> Path:
    body = text_para("Договор с макросами. 1. Предмет договора.")
    return build_docx(OUT / "05_edge_with_macros.docx", body, with_macros=True)


def sample_broken() -> Path:
    path = OUT / "06_edge_broken.docx"
    path.write_bytes(b"PK\x03\x04 not really a zip at all")
    return path


def sample_not_docx() -> Path:
    path = OUT / "07_edge_plain.txt"
    path.write_text("Это не docx, а обычный текстовый файл.", encoding="utf-8")
    return path


def sample_zip_without_document() -> Path:
    """Валидный zip, но без word/document.xml."""
    path = OUT / "08_edge_zip_without_document.docx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("hello.txt", "no word here")
    return path


def sample_xml_comment() -> Path:
    """document.xml с XML-комментарием в body — так делают конвертеры."""
    body = (
        text_para("ДОГОВОР ПОДРЯДА № 5")
        + "<!-- сгенерировано конвертером -->"
        + text_para(
            'ООО "Тета", именуемое в дальнейшем "Заказчик", и ООО "Йота", '
            'именуемое в дальнейшем "Подрядчик", заключили настоящий Договор.'
        )
        + para(run("1. Подрядчик выполняет работы ") + ins("в срок до 31.12.2026"))
    )
    return build_docx(OUT / "09_edge_xml_comment.docx", body)


def sample_renumbering() -> Path:
    """Новый пункт вставлен в СЕРЕДИНУ раздела — все последующие номера сдвигаются.

    Проверяет, на какие номера ссылается протокол: на нумерацию исходного
    договора (как ожидает юрист) или на нумерацию после принятия правок.
    """
    body = "".join([
        text_para("ДОГОВОР ПОСТАВКИ № 99"),
        text_para(
            'ООО "Каппа", именуемое в дальнейшем "Поставщик", и '
            'ООО "Лямбда", именуемое в дальнейшем "Покупатель", заключили настоящий Договор.'
        ),
        text_para("Предмет договора", num_id=1, ilvl=0),
        # исходный 1.1 — без правок
        text_para("Поставщик поставляет товар по заявкам Покупателя.", num_id=1, ilvl=1),
        # вставлен новый пункт В СЕРЕДИНУ: после принятия он станет 1.2
        para(
            ins("Заявка направляется в электронном виде и подтверждается Поставщиком."),
            num_id=1, ilvl=1, para_mark="ins",
        ),
        # исходный 1.2 с правкой: в исходном договоре это пункт 1.2,
        # после вставки Word покажет его как 1.3
        para(
            run("Срок поставки — ") + dele("14") + ins("7") + run(" календарных дней."),
            num_id=1, ilvl=1,
        ),
        text_para("Приёмка товара осуществляется по количеству и качеству.", num_id=1, ilvl=1),
    ])
    return build_docx(OUT / "10_edge_renumbering.docx", body, numbering=numbering_xml())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    made = [
        sample_simple(),
        sample_medium(),
        sample_complex(),
        sample_clean(),
        sample_macros(),
        sample_broken(),
        sample_not_docx(),
        sample_zip_without_document(),
        sample_xml_comment(),
        sample_renumbering(),
    ]
    for path in made:
        print(f"{path.name:44s} {path.stat().st_size:>8d} B")


if __name__ == "__main__":
    main()
