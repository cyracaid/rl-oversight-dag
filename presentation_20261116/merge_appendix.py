"""Merge the four feedback-appendix slides into the main proposal deck.

python-pptx cannot copy slides between presentations, so this walks every shape,
deep-copies its XML, and re-binds picture relationships to the target package.

Output: Team6_Proposal_with_feedback.pptx (14 slides). The source decks are not
modified.
"""
from copy import deepcopy
from io import BytesIO
from pathlib import Path

from pptx import Presentation
from pptx.oxml.ns import qn

HERE = Path(__file__).resolve().parent
APPENDIX = HERE / 'Team6_Feedback_Appendix.pptx'
PROPOSAL = HERE / 'Team6_Proposal.pptx'
OUTPUT = HERE / 'Team6_Proposal_with_feedback.pptx'

# A1-A3 go after the motivation slide, before the MDP. A4 keeps its appendix
# role and goes to the back, because it is a denominators caveat, not a step.
INSERT_AFTER = 2
INLINE_COUNT = 3


def copy_slide(source_slide, target_prs):
    target = target_prs.slides.add_slide(target_prs.slide_layouts[6])
    for placeholder in list(target.placeholders):
        placeholder._element.getparent().remove(placeholder._element)

    source_part = source_slide.part
    for shape in source_slide.shapes:
        element = deepcopy(shape._element)
        for blip in element.iter(qn('a:blip')):
            old_rid = blip.get(qn('r:embed'))
            if old_rid is None:
                continue
            image_part = source_part.related_part(old_rid)
            _, new_rid = target.part.get_or_add_image_part(BytesIO(image_part.blob))
            blip.set(qn('r:embed'), new_rid)
        target.shapes._spTree.append(element)

    if source_slide.has_notes_slide:
        text = source_slide.notes_slide.notes_text_frame.text
        if text.strip():
            target.notes_slide.notes_text_frame.text = text
    return target


def renumber_footers(prs):
    """Inserting slides shifts page numbers, so rewrite each NN | PROJECT PROPOSAL
    footer to the slide's real position. Appendix slides keep their A1-A4 kickers."""
    for index, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                text = paragraph.text.strip()
                if text.endswith('PROJECT PROPOSAL') and text[:2].isdigit():
                    runs = paragraph.runs
                    if len(runs) == 1:
                        runs[0].text = f'{index:02d}{runs[0].text[2:]}'
                    else:
                        numbers = [run for run in runs if run.text.strip()]
                        if numbers:
                            numbers[0].text = f'{index:02d}'


def main():
    appendix = Presentation(APPENDIX)
    proposal = Presentation(PROPOSAL)
    original = len(proposal.slides)

    for slide in appendix.slides:
        copy_slide(slide, proposal)

    sld_id_list = proposal.slides._sldIdLst
    inline = list(sld_id_list)[original:original + INLINE_COUNT]
    for element in inline:
        sld_id_list.remove(element)
    for offset, element in enumerate(inline):
        sld_id_list.insert(INSERT_AFTER + offset, element)

    renumber_footers(proposal)

    proposal.core_properties.title = 'Team 6 - proposal with feedback appendix'
    proposal.save(OUTPUT)

    check = Presentation(OUTPUT)
    print(f'{OUTPUT.name}: {len(check.slides)} slides')
    for index, slide in enumerate(check.slides, 1):
        texts = [shape.text_frame.text.strip().replace('\n', ' | ')
                 for shape in slide.shapes
                 if shape.has_text_frame and shape.text_frame.text.strip()]
        print(f'{index:2d} | {" ## ".join(texts)[:110]}')


if __name__ == '__main__':
    main()
