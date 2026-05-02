from scrapers.albert_scraper import rows_to_documents


def test_rows_to_documents_promotes_topic_line_to_title_not_description():
    rows = [
        {
            "code": "ENGL-UA 59",
            "section": "001",
            "crn": "22420",
            "status": "Open",
            "source_row": [
                "ENGL-UA 59 Topics:",
                "Of Monsters and Medicine",
                "Topics and prerequisites vary by semester.",
                "School:",
                "College of Arts and Science",
                "Term:Fall 2026",
                "Topic: Of Monsters and Medicine",
                "ENGL-UA 59 | 4 units",
                "Class#: 22420",
                "Section: 001",
                "Class Status: Open",
                "Component: Lecture",
                "Visit the Bookstore",
            ],
        }
    ]

    docs = rows_to_documents(rows, term_code="Fall 2026", source_url="test")

    assert docs[0]["title"] == "Topics: Of Monsters and Medicine"
    assert docs[0]["topic"] == "Of Monsters and Medicine"
    assert docs[0]["description"] == "Topics and prerequisites vary by semester."


def test_rows_to_documents_realigns_shifted_topic_to_next_section():
    rows = [
        {
            "code": "CSCI-UA 480",
            "section": "062",
            "crn": "21315",
            "status": "Open",
            "source_row": [
                "CSCI-UA 480 Special Topics:",
                "Term:Fall 2026",
                "Topic: Introduction to Computer Security",
                "CSCI-UA 480 | 4 units",
                "Class#: 21315",
                "Section: 062",
                "Class Status: Open",
                "Component: Lecture",
                "Visit the Bookstore",
            ],
        },
        {
            "code": "CSCI-UA 480",
            "section": "063",
            "crn": "8977",
            "status": "Open",
            "source_row": [
                "CSCI-UA 480 | 4 units",
                "Class#: 8977",
                "Section: 063",
                "Class Status: Open",
                "Component: Lecture",
                "Visit the Bookstore",
                "Topic: Technology, Law, and Policy",
            ],
        },
        {
            "code": "CSCI-UA 480",
            "section": "076",
            "crn": "22206",
            "status": "Open",
            "source_row": [
                "CSCI-UA 480 | 4 units",
                "Class#: 22206",
                "Section: 076",
                "Class Status: Open",
                "Component: Lecture",
                "Visit the Bookstore",
            ],
        },
    ]

    docs = rows_to_documents(rows, term_code="Fall 2026", source_url="test")
    by_section = {doc["section"]: doc for doc in docs}

    assert by_section["063"]["topic"] == "Introduction to Computer Security"
    assert by_section["076"]["topic"] == "Technology, Law, and Policy"
    assert by_section["063"]["source"]["raw_row"][-1] == "Visit the Bookstore"
    assert by_section["076"]["source"]["raw_row"][0] == "Topic: Technology, Law, and Policy"
