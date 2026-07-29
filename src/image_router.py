"""
Positional image router — the FALLBACK used when AI analysis isn't available.

When the holistic AI analysis (ai_extractor.analyze_question) has classified the
images, the UI uses those roles directly. This module is only used when there is
no AI result, applying a simple, reliable rule based on how ExamTopics lays out
image questions:

  - 1 image  -> it's the question exhibit (show it).
  - 2+ images -> the LAST image is the correct-answer key (hide in practice);
                 the rest are the question exhibit(s).

split_images never returns an empty practice list when images exist, so the user
is never left with nothing to look at.
"""


def split_images(images, categories=None):
    """
    images     : list[str] image paths (already existence-checked)
    categories : optional {path: role}; if it flags any 'answer_key'/'other'
                 those are treated as the answer/hidden set.
    Returns (practice_images, answer_images).
    """
    imgs = list(images or [])
    if not imgs:
        return [], []
    if len(imgs) == 1:
        return imgs, []

    if categories:
        answer = [p for p in imgs if categories.get(p) in ("answer_key", "other")]
        practice = [p for p in imgs if p not in answer]
        if answer and practice:
            return practice, answer

    # Positional fallback: last image is the correct-answer key.
    return imgs[:-1], imgs[-1:]


def practice_images(images, categories=None):
    return split_images(images, categories)[0]


def answer_images(images, categories=None):
    return split_images(images, categories)[1]
