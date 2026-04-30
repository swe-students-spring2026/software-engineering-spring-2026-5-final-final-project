"storage helper functions"

from datetime import datetime


def make_doc(url, summary, top, bottom, image):
    "creating dict for atorigng meme"
    return {
        "url": url,
        "summary": summary,
        "top": top,
        "bottom": bottom,
        "image": image,
        "created_at": datetime.now().isoformat(),
    }
