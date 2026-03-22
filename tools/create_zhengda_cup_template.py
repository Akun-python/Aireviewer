from __future__ import annotations

import argparse
from pathlib import Path


PT = {
    "三号": 16,
    "小三": 15,
    "四号": 14,
    "小四": 12,
    "五号": 10.5,
}


def _apply_paragraph_format(
    style,
    *,
    alignment: int | None = None,
    line_spacing_rule: int | None = None,
    line_spacing_pt: float | None = None,
    space_before_pt: float | None = None,
    space_after_pt: float | None = None,
    space_before_auto: bool | None = None,
    space_after_auto: bool | None = None,
    first_line_indent_pt: float | None = None,
) -> None:
    pf = style.ParagraphFormat
    if alignment is not None:
        pf.Alignment = alignment
    if line_spacing_rule is not None:
        pf.LineSpacingRule = line_spacing_rule
    if line_spacing_pt is not None:
        pf.LineSpacing = line_spacing_pt
    if space_before_pt is not None:
        pf.SpaceBefore = space_before_pt
    if space_after_pt is not None:
        pf.SpaceAfter = space_after_pt
    if space_before_auto is not None:
        pf.SpaceBeforeAuto = space_before_auto
    if space_after_auto is not None:
        pf.SpaceAfterAuto = space_after_auto
    if first_line_indent_pt is not None:
        pf.FirstLineIndent = first_line_indent_pt


def _apply_font(style, *, east_asia: str, ascii_font: str, size_pt: float, bold: bool) -> None:
    font = style.Font
    font.NameFarEast = east_asia
    font.Name = ascii_font
    font.Size = size_pt
    font.Bold = bool(bold)


def build_zhengda_cup_dotx(out_path: Path) -> None:
    try:
        import win32com.client as win32  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("缺少 pywin32：请先安装 `pywin32`。") from exc

    word = None
    doc = None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cm_to_pt = 28.346456692913385

    # Word constants (avoid makepy/typelib dependency).
    # FileFormat for .dotx (verified in this environment): 14 => template.main+xml
    wdFormatXMLTemplate = 14
    wdPaperA4 = 7
    wdOrientPortrait = 0
    wdAlignParagraphCenter = 1
    wdAlignParagraphJustify = 3
    wdLineSpaceSingle = 0
    wdLineSpaceMultiple = 5

    # List gallery / behavior constants used by ApplyListTemplateWithLevel.
    wdOutlineNumberGallery = 3
    wdListApplyToWholeList = 0
    wdWord10ListBehavior = 2

    try:
        word = win32.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0

        doc = word.Documents.Add()

        page = doc.PageSetup
        page.PaperSize = wdPaperA4
        page.Orientation = wdOrientPortrait
        page.TopMargin = 2.54 * cm_to_pt
        page.BottomMargin = 2.54 * cm_to_pt
        page.LeftMargin = 3.18 * cm_to_pt
        page.RightMargin = 3.18 * cm_to_pt

        styles = doc.Styles

        # --- Base styles ---
        # Built-in style ids (language-independent)
        wdStyleNormal = -1
        wdStyleHeading1 = -2
        wdStyleHeading2 = -3
        wdStyleHeading3 = -4
        wdStyleHeading4 = -5
        wdStyleHeading5 = -6
        wdStyleTitle = -63
        wdStyleCaption = -35
        wdStyleFootnoteText = -30

        normal = styles(wdStyleNormal)
        _apply_font(normal, east_asia="宋体", ascii_font="Times New Roman", size_pt=PT["小四"], bold=False)
        _apply_paragraph_format(
            normal,
            alignment=wdAlignParagraphJustify,
            line_spacing_rule=wdLineSpaceMultiple,
            line_spacing_pt=PT["小四"] * 1.25,
            space_before_pt=PT["小四"] * 0.5,
            space_after_pt=0,
            first_line_indent_pt=PT["小四"] * 2,  # 2 个汉字缩进（近似）
        )

        title = styles(wdStyleTitle)
        _apply_font(title, east_asia="宋体", ascii_font="Times New Roman", size_pt=PT["三号"], bold=True)
        _apply_paragraph_format(
            title,
            alignment=wdAlignParagraphCenter,
            line_spacing_rule=wdLineSpaceSingle,
            space_before_auto=True,
            space_after_auto=True,
            first_line_indent_pt=0,
        )

        h1 = styles(wdStyleHeading1)
        _apply_font(h1, east_asia="黑体", ascii_font="Arial", size_pt=PT["小三"], bold=False)
        _apply_paragraph_format(
            h1,
            alignment=wdAlignParagraphJustify,
            line_spacing_rule=wdLineSpaceMultiple,
            line_spacing_pt=PT["小四"] * 1.25,
            space_before_pt=PT["小四"] * 0.5,
            space_after_pt=0,
            first_line_indent_pt=0,
        )

        h2 = styles(wdStyleHeading2)
        _apply_font(h2, east_asia="黑体", ascii_font="Arial", size_pt=PT["四号"], bold=False)
        _apply_paragraph_format(
            h2,
            alignment=wdAlignParagraphJustify,
            line_spacing_rule=wdLineSpaceMultiple,
            line_spacing_pt=PT["小四"] * 1.25,
            space_before_pt=PT["小四"] * 0.5,
            space_after_pt=0,
            first_line_indent_pt=0,
        )

        # Other headings: same as正文（规范中未要求加粗）
        for style_id in (wdStyleHeading3, wdStyleHeading4, wdStyleHeading5):
            h = styles(style_id)
            _apply_font(h, east_asia="宋体", ascii_font="Times New Roman", size_pt=PT["小四"], bold=False)
            _apply_paragraph_format(
                h,
                alignment=wdAlignParagraphJustify,
                line_spacing_rule=wdLineSpaceMultiple,
                line_spacing_pt=PT["小四"] * 1.25,
                space_before_pt=PT["小四"] * 0.5,
                space_after_pt=0,
                first_line_indent_pt=0,
            )

        caption = styles(wdStyleCaption)
        _apply_font(caption, east_asia="宋体", ascii_font="Times New Roman", size_pt=PT["小四"], bold=False)
        _apply_paragraph_format(
            caption,
            alignment=wdAlignParagraphCenter,
            line_spacing_rule=wdLineSpaceSingle,
            space_before_pt=0,
            space_after_pt=0,
            first_line_indent_pt=0,
        )

        footnote_text = styles(wdStyleFootnoteText)
        _apply_font(footnote_text, east_asia="宋体", ascii_font="Times New Roman", size_pt=PT["小四"], bold=False)
        _apply_paragraph_format(
            footnote_text,
            alignment=wdAlignParagraphJustify,
            line_spacing_rule=wdLineSpaceSingle,
            space_before_pt=0,
            space_after_pt=0,
            first_line_indent_pt=0,
        )

        # Optional: a dedicated table paragraph style (won't auto-apply, but useful to have).
        try:
            wdStyleTypeParagraph = 1
            table_text_style = styles.Add("正大杯_表格文字", wdStyleTypeParagraph)
            _apply_font(
                table_text_style,
                east_asia="宋体",
                ascii_font="Times New Roman",
                size_pt=PT["小四"],
                bold=False,
            )
            _apply_paragraph_format(
                table_text_style,
                alignment=wdAlignParagraphJustify,
                line_spacing_rule=wdLineSpaceSingle,
                space_before_pt=0,
                space_after_pt=0,
                first_line_indent_pt=0,
            )
        except Exception:
            pass

        # --- Captions labels (best-effort; separator "空两格" cannot be guaranteed by Word template alone) ---
        try:
            for label in ("图", "表", "附注", "公式"):
                try:
                    word.CaptionLabels(label)
                except Exception:
                    word.CaptionLabels.Add(label)
        except Exception:
            pass

        # --- Multilevel numbering: 一、（一）1.（1）1） ---
        # Key: NumberStyle=39 gives Chinese numerals (一二三...) on this machine.
        lt = doc.ListTemplates.Add(True)
        lt.Name = "正大杯_多级编号"

        h1_name = h1.NameLocal
        h2_name = h2.NameLocal
        h3_name = styles(wdStyleHeading3).NameLocal
        h4_name = styles(wdStyleHeading4).NameLocal
        h5_name = styles(wdStyleHeading5).NameLocal

        def _setup_level(
            level: int,
            *,
            number_style: int,
            number_format: str,
            linked_style_name: str,
            left_indent_pt: float,
            tab_position_pt: float,
        ) -> None:
            ll = lt.ListLevels(level)
            ll.NumberStyle = number_style
            ll.NumberFormat = number_format
            ll.LinkedStyle = linked_style_name
            ll.TrailingCharacter = 0  # tab
            ll.NumberPosition = left_indent_pt
            ll.TextPosition = tab_position_pt
            ll.TabPosition = tab_position_pt
            ll.ResetOnHigher = level - 1
            ll.StartAt = 1
            linked_style = styles(linked_style_name)
            ll.Font.NameFarEast = linked_style.Font.NameFarEast
            ll.Font.Name = linked_style.Font.Name
            ll.Font.Size = linked_style.Font.Size
            ll.Font.Bold = linked_style.Font.Bold
            ll.Alignment = 0
            ll.TextPosition = tab_position_pt

        base_indent = PT["小四"] * 2
        _setup_level(
            1,
            number_style=39,
            number_format="%1、",
            linked_style_name=h1_name,
            left_indent_pt=0,
            tab_position_pt=base_indent,
        )
        _setup_level(
            2,
            number_style=39,
            number_format="（%2）",
            linked_style_name=h2_name,
            left_indent_pt=0,
            tab_position_pt=base_indent,
        )
        _setup_level(
            3,
            number_style=0,
            number_format="%3.",
            linked_style_name=h3_name,
            left_indent_pt=0,
            tab_position_pt=base_indent,
        )
        _setup_level(
            4,
            number_style=0,
            number_format="（%4）",
            linked_style_name=h4_name,
            left_indent_pt=0,
            tab_position_pt=base_indent,
        )
        _setup_level(
            5,
            number_style=0,
            number_format="%5）",
            linked_style_name=h5_name,
            left_indent_pt=0,
            tab_position_pt=base_indent,
        )

        # Attach list template into the outline gallery so users can apply easily.
        try:
            word.ListGalleries(wdOutlineNumberGallery).ListTemplates.Add(False, lt.Name)
        except Exception:
            pass

        # Make Heading 1-5 use the list template by default (best-effort).
        try:
            # Apply once to store it in template context
            rng = doc.Range(0, 0)
            rng.Text = "占位标题\\r"
            para = doc.Paragraphs(1)
            para.Range.Style = styles(wdStyleHeading1)
            para.Range.ListFormat.ApplyListTemplateWithLevel(
                lt,
                ContinuePreviousList=False,
                ApplyTo=wdListApplyToWholeList,
                DefaultListBehavior=wdWord10ListBehavior,
            )
            para.Range.Delete()
        except Exception:
            pass

        # Save as dotx
        if out_path.exists():
            out_path.unlink()
        doc.SaveAs2(str(out_path), FileFormat=wdFormatXMLTemplate)
    finally:
        try:
            if doc is not None:
                doc.Close(False)
        except Exception:
            pass
        try:
            if word is not None:
                word.Quit()
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="生成《正大杯报告格式》Word 模板（.dotx）")
    parser.add_argument(
        "--out",
        type=str,
        default=str(Path("templates") / "正大杯报告格式.dotx"),
        help="输出 dotx 路径（默认：templates/正大杯报告格式.dotx）",
    )
    args = parser.parse_args()

    out_path = Path(args.out).resolve()
    build_zhengda_cup_dotx(out_path)
    print(f"OK: {out_path}")


if __name__ == "__main__":
    main()
