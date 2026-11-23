"""Generate Korean visualizations and build 개선과정.docx for Role 2."""

import struct
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from matplotlib import font_manager, rc_context
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"

INK = "#162E40"
MUTED = "#4B6372"
TEAL = "#006C66"
CORAL = "#C85A32"
BLUE = "#2B5B84"
GRAY = "#8C9BA5"
PALE_BG = "#F4F8F7"
CARD_BG = "#FFFFFF"
BORDER = "#D0DSE0"


def get_korean_font() -> str:
    fonts = ["Malgun Gothic", "Noto Sans CJK KR", "Noto Sans KR", "Apple SD Gothic Neo"]
    installed = set(font_manager.get_font_names())
    family = next((f for f in fonts if f in installed), None)
    if not family:
        raise RuntimeError("Korean font not found")
    return family


def render_stage_chart(out_path: Path) -> None:
    """Render a 2x2 visual chart showing Starting Point -> Stage 1 -> Stage 2 -> Stage 3."""
    family = get_korean_font()
    with rc_context({"font.family": family, "axes.unicode_minus": False}):
        fig = Figure(figsize=(12.8, 10.2), facecolor="#FFFFFF")
        fig.text(
            0.03,
            0.955,
            "Role 2 단계별 개선 과정: 16곳 검토 후 남은 최종 결론 오류 수 비교",
            fontsize=19,
            weight="bold",
            color=INK,
            va="center",
        )
        fig.text(
            0.03,
            0.920,
            "작업 흐름 200개 평균 (최종 결론 20개 중 틀린 개수 · 막대가 짧을수록 성능이 우수함)",
            fontsize=12,
            color=MUTED,
            va="center",
        )

        panels = [
            {
                "pos": [0.18, 0.56, 0.28, 0.26],
                "title": "출발점 · 정상 점수 vs 유형 내 뒤섞인 점수",
                "subtitle": "같은 유형 안에서 점수가 바뀌면 평균만으로는 이상 탐지 불가",
                "labels": [
                    "정상 점수 · 기존 규칙",
                    "정상 점수 · 기존 GNN",
                    "점수 뒤섞임 · 처음부터 무시",
                    "점수 뒤섞임 · 그대로 신뢰",
                ],
                "values": [1.130, 1.485, 3.150, 4.085],
                "colors": [TEAL, BLUE, GRAY, CORAL],
                "note": "→ 질문: 검토 도중에 점수가 엉터리인지 알아낼 수 없을까?",
            },
            {
                "pos": [0.68, 0.56, 0.28, 0.26],
                "title": "1차 · 검토 결과 피드백으로 점수 신뢰 여부 갱신",
                "subtitle": "조건: 같은 유형 내 점수 뒤섞임 (실제 발견 결과와 대조)",
                "labels": [
                    "기존 규칙 + 실시간 피드백",
                    "기존 규칙 (고정)",
                    "기존 GNN + 실시간 피드백",
                    "기존 GNN (고정)",
                ],
                "values": [3.075, 3.820, 3.853, 4.083],
                "colors": [TEAL, GRAY, BLUE, CORAL],
                "note": "→ 질문: 규칙이 더 잘 줄이는데, GNN이 규칙 순위에서 출발하면?",
            },
            {
                "pos": [0.18, 0.12, 0.28, 0.26],
                "title": "2차 · 규칙 순위 기반 강화학습 보정 (잔차 GNN)",
                "subtitle": "조건: 같은 유형 내 점수 뒤섞임 (동일 데이터·학습량 훈련)",
                "labels": [
                    "기존 규칙 단독",
                    "규칙 순위 + GNN 보정",
                    "스스로 순위를 정한 GNN",
                ],
                "values": [2.660, 2.682, 4.543],
                "colors": [GRAY, TEAL, CORAL],
                "note": "→ 질문: 규칙 출발은 큰 도움이 됐으나 추가 이득 없음. 한 수 앞을 내다보면?",
            },
            {
                "pos": [0.68, 0.12, 0.28, 0.26],
                "title": "3차 · 현재 1단계 선택 vs 다음 선택까지 2단계 계산",
                "subtitle": "조건: 같은 유형 내 점수 뒤섞임 (오류 발견·미발견 시나리오 계산)",
                "labels": [
                    "1단계 앞보기 규칙",
                    "2단계 앞보기 (한 수 앞 계산)",
                ],
                "values": [3.075, 3.110],
                "colors": [TEAL, BLUE],
                "note": "→ 200개 중 183개 동일. 부분 손상·보상 개선 후속 실험으로 이동",
            },
        ]

        for p in panels:
            ax = fig.add_axes(p["pos"], facecolor=PALE_BG)
            labels = list(reversed(p["labels"]))
            values = list(reversed(p["values"]))
            colors = list(reversed(p["colors"]))
            y_pos = range(len(labels))

            bars = ax.barh(y_pos, values, height=0.52, color=colors, edgecolor="none")
            ax.set_yticks(list(y_pos))
            ax.set_yticklabels(labels, fontsize=10.2, color=INK, weight="bold")
            ax.set_xlim(0, 5.4)
            ax.xaxis.grid(True, linestyle="--", alpha=0.5, color="#B8C8C6")
            ax.set_axisbelow(True)
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
            ax.spines["left"].set_color("#8CA3A0")
            ax.spines["bottom"].set_color("#8CA3A0")
            ax.tick_params(axis="x", labelsize=9.5, colors=MUTED)

            for bar, val in zip(bars, values):
                ax.text(
                    val + 0.09,
                    bar.get_y() + bar.get_height() / 2,
                    f"{val:.3f}개",
                    va="center",
                    ha="left",
                    fontsize=10.2,
                    weight="bold",
                    color=INK,
                )

            ax.text(
                -0.52,
                1.16,
                p["title"],
                transform=ax.transAxes,
                fontsize=12.5,
                weight="bold",
                color=INK,
                va="bottom",
            )
            ax.text(
                -0.52,
                1.04,
                p["subtitle"],
                transform=ax.transAxes,
                fontsize=9.6,
                color=MUTED,
                va="bottom",
            )
            ax.text(
                -0.52,
                -0.22,
                p["note"],
                transform=ax.transAxes,
                fontsize=10.0,
                weight="bold",
                color=TEAL,
                va="top",
            )

        fig.savefig(out_path, dpi=180)


def render_followup_chart(out_path: Path) -> None:
    """Render a 3-row horizontal bar chart with right-side takeaway boxes for the 3 follow-up experiments."""
    family = get_korean_font()
    with rc_context({"font.family": family, "axes.unicode_minus": False}):
        fig = Figure(figsize=(12.4, 8.6), facecolor="#FFFFFF")
        fig.text(
            0.03,
            0.95,
            "후속 실험 3가지 핵심 검증 결과 (막대가 짧을수록 남은 오류가 적음)",
            fontsize=18,
            weight="bold",
            color=INK,
            va="center",
        )
        fig.text(
            0.03,
            0.912,
            "앞선 1~3차 실험에서 남은 의문(부분 손상, 강화학습 보상 설계, 실제 수면일기 데이터 적용)을 별도로 검증",
            fontsize=11.5,
            color=MUTED,
            va="center",
        )

        rows = [
            {
                "pos": [0.22, 0.64, 0.43, 0.19],
                "title": "① 부분 손상 검증 · 5개 유형 중 2개 유형의 점수만 뒤섞였을 때",
                "labels": ["점수를 계속 신뢰", "검토 결과로 실시간 피드백", "점수를 계속 무시"],
                "values": [2.180, 2.280, 2.820],
                "colors": [BLUE, TEAL, CORAL],
                "xlim": 3.5,
                "fmt": "{:.3f}개",
                "box_title": "핵심 판정 (2개 유형 손상 기준)",
                "box_lines": [
                    "• 실시간 피드백(2.280개)은 점수를",
                    "  계속 무시할 때(2.820개)보다",
                    "  평균 0.540개 오류 감소",
                    "• 3개 유형 손상 시에는 피드백이",
                    "  2.500개로 세 방식 중 오류 최소",
                ],
            },
            {
                "pos": [0.22, 0.35, 0.43, 0.20],
                "title": "② 보상 설계 개선 · 각 검토 선택 이후의 성과만 보상으로 반영했을 때",
                "labels": [
                    "독립 확인 · 2단계 규칙",
                    "독립 확인 · 보상 개선 GNN",
                    "보상 개선 GNN (선택 이후만)",
                    "기존 보상 GNN (총성과 일괄)",
                ],
                "values": [2.765, 2.945, 2.926, 4.549],
                "colors": [GRAY, BLUE, TEAL, CORAL],
                "xlim": 5.4,
                "fmt": "{:.3f}개",
                "box_title": "핵심 판정 (전체 유형 점수 뒤섞임)",
                "box_lines": [
                    "• 보상 방식을 바꾸자 GNN 잔여 오류가",
                    "  4.549 → 2.926개로 1.623개 대폭 감소",
                    "• 학습 시드 5개 모두 일관되게 개선",
                    "• 새 그래프 200개 독립 비교에서는",
                    "  2단계 규칙(2.765개)이 0.180개 우세",
                ],
            },
            {
                "pos": [0.22, 0.06, 0.43, 0.20],
                "title": "③ 실제 데이터 재생 · KAIST 공개 수면일기(평가 41명)에서 2박 검토",
                "labels": [
                    "첫날 결과 반영 규칙 (2박)",
                    "기존 품질 규칙 (2박)",
                    "연속 이틀 선택 규칙 (2박)",
                    "검토 전 (오류 주입 상태)",
                ],
                "values": [0.02341, 0.02388, 0.02389, 0.10139],
                "colors": [TEAL, GRAY, BLUE, CORAL],
                "xlim": 0.125,
                "fmt": "{:.5f}개",
                "box_title": "핵심 판정 (판단 3개 중 달라진 수)",
                "box_lines": [
                    "• 2박 검토만으로 오류는 0.10139에서",
                    "  0.02388개로 약 76% 감소",
                    "• 연속 이틀 선택(0.02389)이나 첫날",
                    "  피드백 반영(0.02341)의 추가 이득은",
                    "  유의미하게 확인되지 않음",
                ],
            },
        ]

        for r in rows:
            ax = fig.add_axes(r["pos"], facecolor=PALE_BG)
            labels = list(reversed(r["labels"]))
            values = list(reversed(r["values"]))
            colors = list(reversed(r["colors"]))
            y_pos = range(len(labels))

            bars = ax.barh(y_pos, values, height=0.55, color=colors, edgecolor="none")
            ax.set_yticks(list(y_pos))
            ax.set_yticklabels(labels, fontsize=10.0, color=INK, weight="bold")
            ax.set_xlim(0, r["xlim"])
            ax.xaxis.grid(True, linestyle="--", alpha=0.5, color="#B8C8C6")
            ax.set_axisbelow(True)
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
            ax.spines["left"].set_color("#8CA3A0")
            ax.spines["bottom"].set_color("#8CA3A0")
            ax.tick_params(axis="x", labelsize=9.0, colors=MUTED)

            offset = r["xlim"] * 0.018
            for bar, val in zip(bars, values):
                ax.text(
                    val + offset,
                    bar.get_y() + bar.get_height() / 2,
                    r["fmt"].format(val),
                    va="center",
                    ha="left",
                    fontsize=10.0,
                    weight="bold",
                    color=INK,
                )

            ax.text(
                -0.44,
                1.08,
                r["title"],
                transform=ax.transAxes,
                fontsize=12.0,
                weight="bold",
                color=INK,
                va="bottom",
            )

            # Right-side summary card
            bx, by, bw, bh = 0.68, r["pos"][1], 0.29, r["pos"][3]
            fig.add_artist(
                Rectangle(
                    (bx, by),
                    bw,
                    bh,
                    transform=fig.transFigure,
                    facecolor="#EAF4F2",
                    edgecolor="#B8D0CE",
                    linewidth=1.0,
                )
            )
            fig.text(
                bx + 0.015,
                by + bh - 0.028,
                r["box_title"],
                fontsize=10.5,
                weight="bold",
                color=TEAL,
                va="top",
            )
            for idx, line in enumerate(r["box_lines"]):
                fig.text(
                    bx + 0.015,
                    by + bh - 0.062 - idx * 0.026,
                    line,
                    fontsize=9.6,
                    color=INK,
                    va="top",
                )

        fig.savefig(out_path, dpi=180)


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    w, h = struct.unpack(">LL", data[16:24])
    return int(w), int(h)


class DocxBuilder:
    """Minimal, self-contained OpenXML (.docx) writer supporting headings, formatting, tables, callouts, and PNGs."""

    def __init__(self) -> None:
        self.body_xml: list[str] = []
        self.images: list[tuple[str, Path]] = []
        self.doc_pr_id = 1

    def _run_xml(self, text: str, bold: bool = False, color: str = "162E40", size_half_pt: int = 21) -> str:
        b_tag = "<w:b/><w:bCs/>" if bold else ""
        return (
            "<w:r>"
            "<w:rPr>"
            '<w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic" w:cs="Malgun Gothic"/>'
            f"{b_tag}"
            f'<w:color w:val="{color}"/>'
            f'<w:sz w:val="{size_half_pt}"/><w:szCs w:val="{size_half_pt}"/>'
            "</w:rPr>"
            f'<w:t xml:space="preserve">{escape(text)}</w:t>'
            "</w:r>"
        )

    def add_rich_paragraph(
        self,
        segments: list[tuple[str, bool, str]],
        space_before: int = 80,
        space_after: int = 140,
        line: int = 320,
        fill: str | None = None,
        border_left_color: str | None = None,
        size_half_pt: int = 21,
    ) -> None:
        shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>' if fill else ""
        bdr = ""
        ind = ""
        if border_left_color:
            bdr = (
                "<w:pBdr>"
                f'<w:left w:val="single" w:sz="24" w:space="12" w:color="{border_left_color}"/>'
                '<w:top w:val="single" w:sz="4" w:space="6" w:color="E0ECEA"/>'
                '<w:bottom w:val="single" w:sz="4" w:space="6" w:color="E0ECEA"/>'
                '<w:right w:val="single" w:sz="4" w:space="8" w:color="E0ECEA"/>'
                "</w:pBdr>"
            )
            ind = '<w:ind w:left="160" w:right="160"/>'
        runs = "".join(self._run_xml(t, bold=b, color=c, size_half_pt=size_half_pt) for t, b, c in segments)
        self.body_xml.append(
            "<w:p>"
            "<w:pPr>"
            f"{bdr}{shd}{ind}"
            f'<w:spacing w:before="{space_before}" w:after="{space_after}" w:line="{line}" w:lineRule="auto"/>'
            "</w:pPr>"
            f"{runs}"
            "</w:p>"
        )

    def add_title(self, title: str, subtitle: str) -> None:
        self.body_xml.append(
            "<w:p>"
            '<w:pPr><w:spacing w:before="40" w:after="80" w:line="300" w:lineRule="auto"/></w:pPr>'
            f'{self._run_xml(title, bold=True, color="162E40", size_half_pt=36)}'
            "</w:p>"
        )
        self.body_xml.append(
            "<w:p>"
            '<w:pPr>'
            '<w:pBdr><w:bottom w:val="single" w:sz="12" w:space="8" w:color="006C66"/></w:pBdr>'
            '<w:spacing w:before="0" w:after="220" w:line="260" w:lineRule="auto"/>'
            "</w:pPr>"
            f'{self._run_xml(subtitle, bold=False, color="4B6372", size_half_pt=20)}'
            "</w:p>"
        )

    def add_heading(self, text: str) -> None:
        self.body_xml.append(
            "<w:p>"
            "<w:pPr>"
            "<w:keepNext/>"
            '<w:pBdr><w:bottom w:val="single" w:sz="6" w:space="4" w:color="B8D0CE"/></w:pBdr>'
            '<w:spacing w:before="280" w:after="120" w:line="280" w:lineRule="auto"/>'
            "</w:pPr>"
            f'{self._run_xml(text, bold=True, color="006C66", size_half_pt=26)}'
            "</w:p>"
        )

    def add_image(self, img_path: Path, caption: str, width_inches: float = 6.2) -> None:
        rel_id = f"rIdImg{len(self.images) + 1}"
        self.images.append((rel_id, img_path))
        px_w, px_h = png_size(img_path)
        cx = int(width_inches * 914400)
        cy = int(cx * (px_h / px_w))
        doc_id = self.doc_pr_id
        self.doc_pr_id += 1

        drawing = (
            "<w:p>"
            '<w:pPr><w:jc w:val="center"/><w:spacing w:before="140" w:after="60"/></w:pPr>'
            "<w:r>"
            "<w:drawing>"
            '<wp:inline distT="0" distB="0" distL="0" distR="0" '
            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
            f'<wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:docPr id="{doc_id}" name="Picture {doc_id}"/>'
            "<wp:cNvGraphicFramePr>"
            '<a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>'
            "</wp:cNvGraphicFramePr>"
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            "<pic:nvPicPr>"
            f'<pic:cNvPr id="{doc_id}" name="{escape(img_path.name)}"/>'
            "<pic:cNvPicPr/>"
            "</pic:nvPicPr>"
            "<pic:blipFill>"
            f'<a:blip r:embed="{rel_id}"/>'
            "<a:stretch><a:fillRect/></a:stretch>"
            "</pic:blipFill>"
            "<pic:spPr>"
            f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            "</pic:spPr>"
            "</pic:pic>"
            "</a:graphicData>"
            "</a:graphic>"
            "</wp:inline>"
            "</w:drawing>"
            "</w:r>"
            "</w:p>"
        )
        self.body_xml.append(drawing)
        self.body_xml.append(
            "<w:p>"
            '<w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="200"/></w:pPr>'
            f'{self._run_xml(caption, bold=False, color="4B6372", size_half_pt=18)}'
            "</w:p>"
        )

    def add_table(self, headers: list[str], rows: list[list[list[tuple[str, bool, str]]]], col_widths: list[int]) -> None:
        grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in col_widths)
        header_cells = ""
        for h, w in zip(headers, col_widths):
            header_cells += (
                "<w:tc>"
                "<w:tcPr>"
                f'<w:tcW w:w="{w}" w:type="dxa"/>'
                '<w:shd w:val="clear" w:color="auto" w:fill="162E40"/>'
                '<w:tcMar><w:top w:w="100" w:type="dxa"/><w:bottom w:w="100" w:type="dxa"/>'
                '<w:left w:w="130" w:type="dxa"/><w:right w:w="130" w:type="dxa"/></w:tcMar>'
                "</w:tcPr>"
                "<w:p>"
                '<w:pPr><w:spacing w:before="20" w:after="20"/></w:pPr>'
                f'{self._run_xml(h, bold=True, color="FFFFFF", size_half_pt=19)}'
                "</w:p>"
                "</w:tc>"
            )
        tr_list = [f"<w:tr>{header_cells}</w:tr>"]

        for r_idx, row in enumerate(rows):
            fill = "F4F8F7" if r_idx % 2 == 1 else "FFFFFF"
            cells = ""
            for cell_segments, w in zip(row, col_widths):
                runs = "".join(self._run_xml(t, bold=b, color=c, size_half_pt=19) for t, b, c in cell_segments)
                cells += (
                    "<w:tc>"
                    "<w:tcPr>"
                    f'<w:tcW w:w="{w}" w:type="dxa"/>'
                    f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>'
                    '<w:tcMar><w:top w:w="100" w:type="dxa"/><w:bottom w:w="100" w:type="dxa"/>'
                    '<w:left w:w="130" w:type="dxa"/><w:right w:w="130" w:type="dxa"/></w:tcMar>'
                    "</w:tcPr>"
                    "<w:p>"
                    '<w:pPr><w:spacing w:before="20" w:after="20" w:line="280" w:lineRule="auto"/></w:pPr>'
                    f"{runs}"
                    "</w:p>"
                    "</w:tc>"
                )
            tr_list.append(f"<w:tr>{cells}</w:tr>")

        tbl_xml = (
            "<w:tbl>"
            "<w:tblPr>"
            '<w:tblW w:w="9360" w:type="dxa"/>'
            "<w:tblBorders>"
            '<w:top w:val="single" w:sz="8" w:space="0" w:color="162E40"/>'
            '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="162E40"/>'
            '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="C8D6D4"/>'
            '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="E2ECEA"/>'
            '<w:left w:val="none"/><w:right w:val="none"/>'
            "</w:tblBorders>"
            "</w:tblPr>"
            f"<w:tblGrid>{grid}</w:tblGrid>"
            + "".join(tr_list)
            + "</w:tbl>"
        )
        self.body_xml.append(tbl_xml)

    def save(self, out_path: Path) -> None:
        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="png" ContentType="image/png"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>"
        )
        root_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/>'
            "</Relationships>"
        )
        doc_rels_items = []
        for idx, (rel_id, _) in enumerate(self.images, start=1):
            doc_rels_items.append(
                f'<Relationship Id="{rel_id}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                f'Target="media/image{idx}.png"/>'
            )
        doc_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(doc_rels_items)
            + "</Relationships>"
        )
        sect_pr = (
            "<w:sectPr>"
            '<w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" '
            'w:header="708" w:footer="708" w:gutter="0"/>'
            "</w:sectPr>"
        )
        document_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            "<w:body>"
            + "".join(self.body_xml)
            + sect_pr
            + "</w:body></w:document>"
        )

        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("_rels/.rels", root_rels)
            zf.writestr("word/_rels/document.xml.rels", doc_rels)
            zf.writestr("word/document.xml", document_xml)
            for idx, (_, img_path) in enumerate(self.images, start=1):
                zf.write(img_path, f"word/media/image{idx}.png")


def build_docx() -> None:
    stage_chart = RESULTS / "개선과정_단계별비교.png"
    followup_chart = RESULTS / "후속실험_비교차트.png"
    render_stage_chart(stage_chart)
    render_followup_chart(followup_chart)

    doc = DocxBuilder()
    doc.add_title(
        "Role 2에서 무엇을 보고 다음 실험을 정했나",
        "제한된 검토 예산(16회) 안에서 최종 결론 오류를 줄이기 위한 단계별 개선 및 후속 검증 기록",
    )

    doc.add_rich_paragraph(
        [
            ("핵심 질문: ", True, "006C66"),
            ("사람이 딱 16곳만 확인할 수 있을 때, 어디부터 살펴봐야 마지막에 틀린 결론이 가장 적게 남을까?", True, "162E40"),
        ],
        fill="EAF4F2",
        border_left_color="006C66",
        size_half_pt=22,
    )

    doc.add_rich_paragraph(
        [
            ("이 실험에서는 서로 연결된 ", False, "162E40"),
            ("작업 항목 80개", True, "162E40"),
            ("로부터 ", False, "162E40"),
            ("최종 결론 20개", True, "162E40"),
            ("가 도출된다. 앞단계의 항목 하나를 고치면 그 항목을 바탕으로 나온 여러 결론이 한꺼번에 바로잡히기도 한다. "
             "프로그램이 검토할 항목을 하나씩 추천하고 모의 검토자가 총 16번의 확인을 마친 뒤, 최종 결론 20개 중 여전히 틀린 채로 "
             "남은 결론이 몇 개인지(작업 흐름 200개의 평균)를 측정했다. 따라서 아래에 나오는 ", False, "162E40"),
            ("‘3.075개’ 같은 숫자는 작을수록 오류가 많이 해결됐다는 뜻", True, "006C66"),
            ("이다.", False, "162E40"),
        ]
    )

    doc.add_rich_paragraph(
        [
            ("초기 비교에서 출발해 ", False, "162E40"),
            ("① 검토 결과를 실시간으로 반영하기 → ② 규칙이 매긴 순위에 강화학습 보정 더하기 → ③ 다음 검토까지 한 수 앞을 미리 계산하기", True, "162E40"),
            ("의 세 단계로 개선을 시도했다. 매 단계마다 새로 만든 그래프 200개로 평가했으므로, 수치들은 각 단계 안에서 비교해 읽으면 된다.", False, "162E40"),
        ]
    )

    doc.add_image(
        stage_chart,
        "그림 1. Role 2 초기 비교(출발점)부터 1~3차 실험까지의 단계별 잔여 오류 수 비교 (막대가 짧을수록 우수)",
        width_inches=6.3,
    )

    # 출발점
    doc.add_heading("출발점 · 컴퓨터가 매긴 점수만 보고 믿을 만한지 알 수 있을까?")
    doc.add_rich_paragraph(
        [
            ("기존 규칙은 컴퓨터가 예측한 ", False, "162E40"),
            ("‘이 항목에 오류가 있을 가능성(신뢰도 점수)’", True, "162E40"),
            ("과 ", False, "162E40"),
            ("‘이 항목을 고치면 몇 개의 결론에 영향을 줄지’", True, "162E40"),
            ("를 함께 고려해 다음 검토 대상을 골랐다. 컴퓨터가 매긴 점수가 정상일 때는 이 규칙이 평균 ", False, "162E40"),
            ("1.130개", True, "006C66"),
            (", 기존 그래프 신경망(GNN)이 ", False, "162E40"),
            ("1.485개", True, "162E40"),
            ("의 오류를 남겼다. GNN은 검토 과정에서 개별 오류를 더 자주 찾아냈지만, 정작 최종 결론을 더 많이 바로잡은 쪽은 규칙이었다.", False, "162E40"),
        ]
    )
    doc.add_rich_paragraph(
        [
            ("문제는 컴퓨터의 점수가 부정확할 때다. 점수 전체가 무작위 값으로 바뀌면 평균 점수가 달라져 이상을 바로 알아챌 수 있다. 하지만 ", False, "162E40"),
            ("같은 유형 안에서 항목 A와 B의 점수만 서로 뒤바뀌면 전체 평균은 그대로", True, "C85A32"),
            (" 유지된다. 실제로 점수를 이렇게 섞어 놓자, 평균만 확인하는 방식은 200개 그래프를 모두 정상이라고 판단했다. "
             "이 엉터리 점수를 그대로 믿고 규칙을 적용하면 남은 오류가 ", False, "162E40"),
            ("4.085개", True, "C85A32"),
            ("로 늘어났고, 차라리 처음부터 점수를 무시하면 ", False, "162E40"),
            ("3.150개", True, "006C66"),
            ("가 남았다.", False, "162E40"),
        ]
    )
    doc.add_rich_paragraph(
        [
            ("다음 실험으로 이어진 질문: ", True, "006C66"),
            ("처음 점수를 받았을 때는 이 점수가 믿을 만한지 알 방법이 없다. 그렇다면 항목을 하나씩 직접 열어 보면서 점수를 믿어도 될지 도중에 알아낼 수는 없을까?", True, "162E40"),
        ],
        fill="F4F8F7",
        border_left_color="006C66",
    )

    # 1차
    doc.add_heading("1차 · 실제로 검토해 본 결과를 보고 점수를 계속 믿을지 결정했다")
    doc.add_rich_paragraph(
        [
            ("시도한 방법. ", True, "006C66"),
            ("항목을 검토할 때마다 ‘점수를 믿는 방식’과 ‘점수를 무시하는 방식’이 각각 이번 항목에서 오류가 나올 가능성을 예측한다. "
             "예를 들어 점수가 “여긴 오류가 있을 가능성이 매우 높다”고 지목한 항목들을 열어 봤는데 계속 아무 문제가 없다면, "
             "실제 결과와 더 잘 들어맞은 방식(점수 무시)으로 무게중심을 옮겨 다음 항목을 고른다. 이 전환은 미리 정한 계산식에 따라 이루어졌고, "
             "기존 GNN의 가중치는 고정해 두었다.", False, "162E40"),
        ]
    )
    doc.add_rich_paragraph(
        [
            ("결과와 다음 질문. ", True, "006C66"),
            ("같은 유형 안에서 점수를 뒤섞어 놓은 조건에서, 검토 결과를 실시간으로 반영하자 남은 오류가 규칙은 ", False, "162E40"),
            ("3.820 → 3.075개", True, "006C66"),
            (", 기존 GNN은 ", False, "162E40"),
            ("4.083 → 3.853개", True, "162E40"),
            ("로 줄었다. 두 방식 모두 개선됐지만, 똑같은 피드백을 주어도 여전히 규칙이 GNN보다 오류를 더 적게 남겼다.", False, "162E40"),
        ]
    )
    doc.add_rich_paragraph(
        [
            ("다음 실험으로 이어진 질문: ", True, "006C66"),
            ("GNN이 처음부터 스스로 순위를 매기게 하지 말고, 규칙이 잘하는 부분을 출발점으로 주면 어떨까?", True, "162E40"),
        ],
        fill="F4F8F7",
        border_left_color="006C66",
    )

    # 2차
    doc.add_heading("2차 · 규칙이 매긴 순위를 출발점으로 삼아 강화학습으로 작은 보정을 더했다")
    doc.add_rich_paragraph(
        [
            ("시도한 방법. ", True, "006C66"),
            ("두 GNN 모델에 동일한 규칙 점수를 입력으로 주었다. 한 모델은 이 점수를 참고만 해서 처음부터 순위를 직접 정했고, "
             "다른 모델은 기본적으로 규칙과 똑같은 항목을 추천하되 학습을 통해 일부 항목의 점수만 조금씩 올리거나 내리도록 했다. "
             "두 모델은 같은 데이터와 학습량으로 훈련했다.", False, "162E40"),
        ]
    )
    doc.add_rich_paragraph(
        [
            ("결과와 다음 질문. ", True, "006C66"),
            ("점수를 뒤섞은 조건에서 순위를 직접 정한 모델은 오류를 ", False, "162E40"),
            ("4.543개", True, "C85A32"),
            (" 남긴 반면, 규칙 순위에 보정만 더한 모델은 ", False, "162E40"),
            ("2.682개", True, "006C66"),
            ("로 성능이 크게 좋아졌다. 규칙이 정한 순위에서 출발하는 것이 GNN에 분명히 도움이 된 것이다. "
             "다만 보정 없이 규칙만 그대로 썼을 때(", False, "162E40"),
            ("2.660개", True, "162E40"),
            (")와 비교하면, 강화학습 보정이 규칙을 뛰어넘는 추가 이득을 내지는 못했다.", False, "162E40"),
        ]
    )
    doc.add_rich_paragraph(
        [
            ("다음 실험으로 이어진 질문: ", True, "006C66"),
            ("지금 고른 항목에서 오류가 나올지 안 나올지에 따라 그다음에 볼 곳까지 한 수 앞을 미리 생각하면 더 나아질까?", True, "162E40"),
        ],
        fill="F4F8F7",
        border_left_color="006C66",
    )

    # 3차
    doc.add_heading("3차 · 이번 검토에서 오류가 나올 때와 안 나올 때의 다음 선택까지 미리 계산했다")
    doc.add_rich_paragraph(
        [
            ("시도한 방법. ", True, "006C66"),
            ("기존의 1단계 방식은 지금 당장 확인했을 때 가장 이득이 커 보이는 항목을 고른다. 반면 2단계 방식은 각 후보 항목마다 "
             "‘여기서 오류가 나오면 다음에 어디를 볼까? 아무것도 안 나오면 어디를 볼까?’까지 한 수 앞을 계산해 본 뒤 지금 열 첫 번째 항목을 고른다. "
             "물론 실제 검토는 한 번에 한 곳씩 진행하고, 결과를 확인한 뒤 다시 다음 수를 계산했다(두 방식 모두 총 16회 검토).", False, "162E40"),
        ]
    )
    doc.add_rich_paragraph(
        [
            ("결과와 남은 질문. ", True, "006C66"),
            ("1단계 방식이 ", False, "162E40"),
            ("3.075개", True, "006C66"),
            (", 2단계 방식이 ", False, "162E40"),
            ("3.110개", True, "162E40"),
            ("로, 200개 작업 흐름 중 183개에서 최종 오류 수가 똑같았다. 한 수 앞을 미리 계산하는 것만으로는 뚜렷한 이득이 확인되지 않았다.", False, "162E40"),
        ]
    )
    doc.add_rich_paragraph(
        [
            ("남은 두 가지 핵심 의문: ", True, "006C66"),
            ("① 전체가 아니라 일부 유형의 점수만 잘못됐을 때도 1차의 피드백 방식이 도움이 될까?  "
             "② 2차에서 GNN이 규칙을 넘지 못한 데에는 학습할 때 성과를 알려 주는(보상을 주는) 방식도 영향을 미쳤을까?", True, "162E40"),
        ],
        fill="F4F8F7",
        border_left_color="006C66",
    )

    if (RESULTS / "role2_summary.png").exists():
        doc.add_image(
            RESULTS / "role2_summary.png",
            "그림 2. 출발점 및 1~3차 실험의 조건별 잔여 오류와 95% 신뢰구간 상세 요약",
            width_inches=6.3,
        )

    # 후속 실험
    doc.add_heading("이번 후속 실험 · 앞에서 남은 질문들을 하나씩 따로 검증했다")

    doc.add_image(
        followup_chart,
        "그림 3. 후속 실험 3가지 검증(부분 점수 손상, 강화학습 보상 설계 개선, 실제 수면일기 적용) 결과 비교",
        width_inches=6.3,
    )

    doc.add_table(
        headers=["앞에서 남은 질문", "이번에 바꾼 것", "확인한 결과"],
        col_widths=[2500, 2760, 4100],
        rows=[
            [
                [("1차의 피드백은 점수가 일부만 잘못돼도 도움이 될까?", True, "162E40")],
                [("5개 유형 중 점수를 섞은 유형의 수를 0개부터 5개까지 늘려 가며 비교했다.", False, "162E40")],
                [
                    ("주요 비교 조건인 ‘2개 유형 손상’에서 계속 신뢰 ", False, "162E40"),
                    ("2.180개", True, "162E40"),
                    (", 계속 무시 ", False, "162E40"),
                    ("2.820개", True, "C85A32"),
                    (", 피드백 반영 ", False, "162E40"),
                    ("2.280개", True, "006C66"),
                    ("였다. 피드백 방식은 점수를 아예 무시할 때보다 분명히 유리했고, 계속 신뢰하는 방식과의 차이는 불확실했다.", False, "162E40"),
                ],
            ],
            [
                [("2차에서 GNN이 학습하는 방식에 개선 여지가 있었을까?", True, "162E40")],
                [("같은 GNN에서 보상을 계산하는 방식만 바꿨다. 예를 들어 6번째 선택을 평가할 때는 이미 그전에 끝난 1~5번째 검토의 성과를 보상으로 받지 않게 했다.", False, "162E40")],
                [
                    ("전체 유형의 점수를 섞은 조건에서 오류가 ", False, "162E40"),
                    ("4.549 → 2.926개", True, "006C66"),
                    ("로 크게 줄었다. 별도의 그래프 200개에서 다시 비교했을 때 새 모델은 ", False, "162E40"),
                    ("2.945개", True, "162E40"),
                    (", 2단계 규칙은 ", False, "162E40"),
                    ("2.765개", True, "006C66"),
                    ("였다. 보상 방식을 바꾸자 GNN 성능이 뚜렷하게 좋아졌지만, 여전히 2단계 규칙이 남긴 오류가 조금 더 적었다.", False, "162E40"),
                ],
            ],
            [
                [("실제 수면일기 데이터에서도 피드백이나 연속 날짜 선택이 도움이 될까?", True, "162E40")],
                [("공개된 KAIST 수면일기에서 연속된 이틀에 입력 오류를 넣고, 참가자당 이틀만 열어 바로잡도록 했다.", False, "162E40")],
                [
                    ("평가 대상 41명에서 수면시간·효율·불규칙성 판단 3개 중 원래 판단과 달라진 개수는 기존 규칙 ", False, "162E40"),
                    ("0.02388개", True, "162E40"),
                    (", 연속 이틀 선택 ", False, "162E40"),
                    ("0.02389개", True, "162E40"),
                    (", 첫날 결과 반영 ", False, "162E40"),
                    ("0.02341개", True, "006C66"),
                    ("로 큰 차이가 없었다. 추가 이득은 확인되지 않았으며, 연구실 원자료와 사람 정정 기록을 쓰는 실험은 중단했다.", False, "162E40"),
                ],
            ],
        ],
    )

    if (RESULTS / "후속실험요약.png").exists():
        doc.add_image(
            RESULTS / "후속실험요약.png",
            "그림 4. Role 2 후속 실험 3가지 과제의 전체 수치 요약 시트",
            width_inches=6.1,
        )

    doc.add_rich_paragraph(
        [
            ("종합 결론. ", True, "006C66"),
            ("참고로 3차 실험에서는 ‘1단계 규칙과 2단계 규칙의 차이’를 비교했다면, 이번 후속 실험에서는 ‘보상 방식을 개선한 GNN이 규칙 기반 방식(2단계 규칙 등)을 넘어설 수 있는지’를 별도로 확인했다. "
             "앞선 세 차례의 실험과 이번 후속 실험을 종합해 보면, 컴퓨터가 준 점수가 부정확할 때 ", False, "162E40"),
            ("검토 결과를 반영하는 피드백", True, "006C66"),
            ("과 ", False, "162E40"),
            ("강화학습의 보상 설계 개선", True, "006C66"),
            ("은 분명한 효과를 보였다. 동시에, 제한된 검토 횟수 안에서 어디를 먼저 볼지 정하는 문제에서는 기존 규칙이 여전히 매우 강력한 기준선(baseline)임을 확인할 수 있었다.", False, "162E40"),
        ],
        space_before=180,
        fill="EAF4F2",
        border_left_color="006C66",
    )

    out_docx = ROOT / "개선과정.docx"
    doc.save(out_docx)
    print(f"Saved: {out_docx} ({out_docx.stat().st_size:,} bytes)")


if __name__ == "__main__":
    build_docx()
