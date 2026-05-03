from scrapers.albert_scraper import extract_rows_from_text, rows_to_documents


def test_extract_rows_from_text_keeps_crosslisted_header_with_primary_code():
    rows = extract_rows_from_text(
        "\n".join(
            [
                "CORE-UA 1 | CORE-UA 9001 Complexities: Oceans",
                "We inhabit a world of complex systems. less description for CORE-UA 1 | CORE-UA 9001 «",
                "School:",
                "College of Arts and Science",
                "Term: Fall 2026",
                "CORE-UA 1 | 4 units",
                "Class#: 9516",
                "Session: 1 09/02/2026 - 12/14/2026",
                "Section: 001",
                "Class Status: Closed",
                "Component: Seminar",
                "09/02/2026 - 12/14/2026 Mon 11.00 AM - 1.30 PM at 194 Mercer St Room 202",
                "Visit the Bookstore",
                "CORE-UA 1 | 4 units",
                "Class#: 9517",
                "Session: 1 09/02/2026 - 12/14/2026",
                "Section: 002",
                "Class Status: Closed",
                "Component: Seminar",
                "09/02/2026 - 12/14/2026 Mon 11.00 AM - 1.30 PM at 31 Washington Pl Room 518",
                "Visit the Bookstore",
            ]
        )
    )

    docs = rows_to_documents(rows, term_code="", source_url="test")

    assert [doc["section"] for doc in docs] == ["001", "002"]
    assert docs[0]["code"] == "CORE-UA 1"
    assert docs[0]["title"] == "Complexities: Oceans"
    assert docs[0]["description"] == "We inhabit a world of complex systems."
    assert "CORE-UA 9001" not in docs[0]["description"]
    assert "|" not in docs[0]["description"]
    assert docs[0]["term"] == "Fall 2026"
    assert docs[1]["title"] == "Complexities: Oceans"
    assert docs[1]["term"] == "Fall 2026"


def test_extract_rows_from_text_keeps_crosslisted_header_with_secondary_code():
    rows = extract_rows_from_text(
        "\n".join(
            [
                "CORE-UA 1 | CORE-UA 9001 Complexities: Oceans",
                "We inhabit a world of complex systems.",
                "School:",
                "College of Arts and Science",
                "Term: Fall 2026",
                "CORE-UA 9001 | 4 units",
                "Class#: 9516",
                "Session: 1 09/02/2026 - 12/14/2026",
                "Section: 001",
                "Class Status: Closed",
                "Component: Seminar",
                "Visit the Bookstore",
            ]
        )
    )

    docs = rows_to_documents(rows, term_code="", source_url="test")

    assert docs[0]["code"] == "CORE-UA 9001"
    assert docs[0]["title"] == "Complexities: Oceans"
    assert docs[0]["description"] == "We inhabit a world of complex systems."
    assert docs[0]["term"] == "Fall 2026"


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


def test_rows_to_documents_keeps_multiple_topic_title_lines_together():
    rows = [
        {
            "code": "ENGL-UA 252",
            "section": "001",
            "crn": "6806",
            "status": "Wait List (1)",
            "source_row": [
                "ENGL-UA 252 Topics:",
                "Contemporary Post-Apocalypticism",
                "Eros and Sexuality in Modern Jewish Lit",
                "Intro to medical Humanities",
                "Modern Chinese Fiction",
                "Since 2000: Contemporary Graphic Narratives",
                "The Ethics of Pastoral",
                "Writing Toward Linguistic Justice",
                "Various topics in English Literature",
                "School:",
                "College of Arts and Science",
                "Term:Fall 2026",
                "Topic: Since 2000: Contemporary Graphic Narratives",
                "ENGL-UA 252 | 4 units",
                "Class#: 6806",
                "Section: 001",
                "Class Status: Wait List (1)",
                "Component: Seminar",
                "Visit the Bookstore",
            ],
        },
        {
            "code": "ENGL-UA 252",
            "section": "002",
            "crn": "6807",
            "status": "Wait List (2)",
            "source_row": [
                "ENGL-UA 252 | 4 units",
                "Class#: 6807",
                "Section: 002",
                "Class Status: Wait List (2)",
                "Component: Seminar",
                "Visit the Bookstore",
                "Topic: The Ethics of Pastoral",
            ],
        },
    ]

    docs = rows_to_documents(rows, term_code="Fall 2026", source_url="test")

    expected_title = (
        "Topics: Contemporary Post-Apocalypticism; Eros and Sexuality in Modern Jewish Lit; "
        "Intro to medical Humanities; Modern Chinese Fiction; "
        "Since 2000: Contemporary Graphic Narratives; The Ethics of Pastoral; "
        "Writing Toward Linguistic Justice; Various topics in English Literature"
    )
    assert docs[0]["title"] == expected_title
    assert docs[0]["description"] == ""
    assert docs[1]["title"] == expected_title


def test_rows_to_documents_splits_topic_list_from_following_description():
    rows = [
        {
            "code": "CORE-UA 400",
            "section": "001",
            "crn": "9336",
            "status": "Open",
            "source_row": [
                "CORE-UA 400 Texts & Ideas: Topics",
                "A Genealogy of Morality",
                "Buddhism and Meditation",
                "Children and Childhood",
                "Frankenstein and His Progeny",
                "Guilt & Sin and Law & Justice",
                "Literature and Automatic Invention",
                "Love, Sex, and Happiness",
                "Media and Democracy",
                "Objectivity",
                "Political Economy from Adam Smith to COVID",
                "Soldiers’ Stories",
                "The Black Radical Tradition",
                "The Making of the Human in Early China",
                "For course description, please consult the College Core Curriculum website: http://core.cas.nyu.edu",
                "School:",
                "College of Arts and Science",
                "Term:Fall 2026",
                "Topic: The Black Radical Tradition",
                "CORE-UA 400 | 4 units",
                "Class#: 9336",
                "Section: 001",
                "Class Status: Open",
                "Component: Lecture",
                "Visit the Bookstore",
            ],
        },
        {
            "code": "CORE-UA 400",
            "section": "002",
            "crn": "9337",
            "status": "Open",
            "source_row": [
                "CORE-UA 400",
                "Class#: 9337",
                "Section: 002",
                "Class Status: Open",
                "Component: Recitation",
                "Visit the Bookstore",
                "Topic: The Black Radical Tradition",
            ],
        },
    ]

    docs = rows_to_documents(rows, term_code="Fall 2026", source_url="test")

    assert docs[0]["title"].startswith("Texts & Ideas: Topics: A Genealogy of Morality; Buddhism")
    assert "The Black Radical Tradition" in docs[0]["title"]
    assert "For course description" not in docs[0]["title"]
    assert docs[0]["description"] == (
        "For course description, please consult the College Core Curriculum website: http://core.cas.nyu.edu"
    )
    assert docs[1]["title"] == docs[0]["title"]


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
