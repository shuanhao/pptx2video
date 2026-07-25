from pathlib import Path
from pptx import Presentation

path = Path(__file__).with_name('sample_test.pptx')
prs = Presentation()

slides_data = [
    {
        'title': 'Cover Page',
        'notes': [],
    },
    {
        'title': 'Page 1',
        'notes': [
            'This is the first paragraph of a long note for page one.',
            '',
            'This is the third paragraph with more detail and a second line of content for page one.',
        ],
    },
    {
        'title': 'Page 2',
        'notes': [
            'This is the opening paragraph for page two.',
            'This is a second paragraph for page two with extra detail.',
            '',
            'This is the final paragraph for page two.',
        ],
    },
    {
        'title': 'Page 3',
        'notes': [
            'This is the first paragraph of a long note for page three.',
            '',
            'This is the third paragraph with even more detail for page three.',
        ],
    },
    {
        'title': 'Q&A / Thanks',
        'notes': [],
    },
]

for slide_data in slides_data:
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = slide_data['title']
    slide.placeholders[1].text = f'Content for {slide_data["title"]}'

    notes_frame = slide.notes_slide.notes_text_frame
    notes_frame.clear()

    for index, paragraph_text in enumerate(slide_data['notes']):
        if index == 0:
            notes_frame.paragraphs[0].text = paragraph_text
        else:
            new_paragraph = notes_frame.add_paragraph()
            new_paragraph.text = paragraph_text

prs.save(path)
print(path.exists(), path)
