from scrapers.albert_scraper import extract_rows_from_text, rows_to_documents


def test_extract_rows_from_text_keeps_crosslisted_header_with_primary_code():
    rows = extract_rows_from_text(
        "\n".join(
            [
                "CORE-UA 1 | CORE-UA 9001 Complexities: Oceans",
                "We inhabit a world of complex systems. less description for CORE-UA 1 | CORE-UA 9001",
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


def test_extract_rows_from_text_uses_header_for_variable_unit_sections():
    rows = extract_rows_from_text(
        "\n".join(
            [
                "ANTH-UA 903 Internship",
                (
                    "Opportunities for students to gain practical work experience sponsored by selected "
                    "institutions are negotiated with the internship sponsor."
                ),
                "School:",
                "College of Arts and Science",
                "Term: Fall 2026",
                "ANTH-UA 903 | 1 - 4 units",
                "Class#: 8393",
                "Session: 1 09/02/2026 - 12/14/2026",
                "Section: 001",
                "Class Status: Open",
                "Component: Seminar",
                "09/02/2026 - 12/14/2026 No Room Required",
                "Notes: Course Repeatable for Credit.",
                "Visit the Bookstore",
                "ANTH-UA 903 | 1 - 4 units",
                "Class#: 8394",
                "Session: 1 09/02/2026 - 12/14/2026",
                "Section: 002",
                "Class Status: Open",
                "Component: Seminar",
                "09/02/2026 - 12/14/2026 No Room Required",
                "Visit the Bookstore",
            ]
        )
    )

    docs = rows_to_documents(rows, term_code="", source_url="test")

    assert [doc["section"] for doc in docs] == ["001", "002"]
    assert docs[0]["title"] == "Internship"
    assert docs[0]["description"].startswith("Opportunities for students")
    assert docs[0]["term"] == "Fall 2026"
    assert docs[1]["title"] == "Internship"
    assert docs[1]["term"] == "Fall 2026"


def test_extract_rows_from_text_uses_header_when_recitations_come_before_lecture():
    rows = extract_rows_from_text(
        "\n".join(
            [
                "PSYCH-UA 1 Introduction to Psychology",
                "Survey of the scientific study of behavior and mental processes.",
                "School:",
                "College of Arts and Science",
                "Term: Fall 2026",
                "PSYCH-UA 1",
                "Class#: 8997",
                "Session: 1 09/02/2026 - 12/14/2026",
                "Section: 002",
                "Class Status: Open",
                "Component: Recitation",
                "09/02/2026 - 12/14/2026 Thu 3.30 PM - 4.45 PM at 40 W 4th St Room LC13",
                "Visit the Bookstore",
                "PSYCH-UA 1 | 4 units",
                "Class#: 9007",
                "Session: 1 09/02/2026 - 12/14/2026",
                "Section: 012",
                "Class Status: Wait List (26)",
                "Component: Lecture",
                "09/02/2026 - 12/14/2026 Mon,Wed 3.30 PM - 4.45 PM at 36 E 8th St Room 200",
                "Visit the Bookstore",
                "PSYCH-UA 1",
                "Class#: 9008",
                "Session: 1 09/02/2026 - 12/14/2026",
                "Section: 013",
                "Class Status: Open",
                "Component: Recitation",
                "09/02/2026 - 12/14/2026 Tue 8.00 AM - 9.15 AM at 7 East 12th St Room 125",
                "Visit the Bookstore",
            ]
        )
    )

    docs = rows_to_documents(rows, term_code="", source_url="test")
    by_section = {doc["section"]: doc for doc in docs}

    assert [doc["section"] for doc in docs] == ["002", "012", "013"]
    assert by_section["002"]["title"] == "Introduction to Psychology"
    assert by_section["002"]["description"] == "Survey of the scientific study of behavior and mental processes."
    assert by_section["002"]["term"] == "Fall 2026"
    assert by_section["012"]["title"] == "Introduction to Psychology"
    assert by_section["012"]["term"] == "Fall 2026"
    assert by_section["013"]["title"] == "Introduction to Psychology"
    assert by_section["013"]["term"] == "Fall 2026"


def test_rows_to_documents_backfills_failed_course_metadata_without_term():
    rows = [
        {
            "code": "PSYCH-UA 1",
            "section": "002",
            "crn": "8997",
            "status": "Open",
            "source_row": [
                "PSYCH-UA 1",
                "Class#: 8997",
                "Session: 1 09/02/2026 - 12/14/2026",
                "Section: 002",
                "Class Status: Open",
                "Component: Recitation",
                "09/02/2026 - 12/14/2026 Thu 3.30 PM - 4.45 PM at 40 W 4th St Room LC13",
                "Visit the Bookstore",
            ],
        },
        {
            "code": "PSYCH-UA 9001",
            "section": "DC1",
            "crn": "9144",
            "status": "Open",
            "source_row": [
                "PSYCH-UA 9001 Intro to Psychology",
                "Fundamental principles of psychology, with emphasis on basic research and applications.",
                "School:",
                "College of Arts and Science",
                "Term: Fall 2026",
                "PSYCH-UA 9001 | 4 units",
                "Class#: 9144",
                "Section: DC1",
                "Class Status: Open",
                "Component: Lecture",
                "Visit the Bookstore",
            ],
        },
    ]

    docs = rows_to_documents(rows, term_code="", source_url="test")
    failed = docs[0]

    assert failed["code"] == "PSYCH-UA 1"
    assert failed["term"] == ""
    assert failed["_id"] == "PSYCH-UA_1_002"
    assert failed["title"] == "Intro to Psychology"
    assert failed["description"] == (
        "Fundamental principles of psychology, with emphasis on basic research and applications."
    )
    assert failed["metadata_fallback"] == {
        "source_code": "PSYCH-UA 9001",
        "fields": ["title", "description"],
    }


def test_extract_rows_from_text_keeps_cbe_recitation_title_lines_before_topic_rows():
    rows = extract_rows_from_text(
        "\n".join(
            [
                "CBE-UY REC CBE Recitation (including BMS, CBE, CM subject areas)",
                "CBE-UY 3153 CBE Thermodynamics",
                "CBE-UY 3313 Heat and Mass Tran",
                "CBE Recitation (including BMS, CBE, CM subject areas)",
                "School:",
                "Tandon School of Engineering",
                "Term: Fall 2026",
                "Topic: CBE-UY 3153 CBE Thermodynamics",
                "CBE-UY REC | 0 units",
                "Class#: 12846",
                "Session: 1 09/02/2026 - 12/14/2026",
                "Section: 3153",
                "Class Status: Open",
                "Component: Recitation",
                "09/02/2026 - 12/14/2026 Fri 2.00 PM - 3.20 PM at Jacobs Hall Room 202",
                "Visit the Bookstore",
                "Topic: CBE-UY 3313 Heat and Mass Tran",
                "CBE-UY REC | 0 units",
                "Class#: 12847",
                "Session: 1 09/02/2026 - 12/14/2026",
                "Section: 3313",
                "Class Status: Open",
                "Component: Recitation",
                "09/02/2026 - 12/14/2026 Fri 12.30 PM - 1.50 PM at Jacobs Hall Room 473",
                "Visit the Bookstore",
            ]
        )
    )

    docs = rows_to_documents(rows, term_code="", source_url="test")

    assert [doc["section"] for doc in docs] == ["3153", "3313"]
    assert docs[0]["title"] == (
        "CBE Recitation (including BMS, CBE, CM subject areas): "
        "CBE-UY 3153 CBE Thermodynamics; CBE-UY 3313 Heat and Mass Tran"
    )
    assert docs[0]["description"] == "CBE Recitation (including BMS, CBE, CM subject areas)"
    assert docs[0]["term"] == "Fall 2026"
    assert docs[1]["title"] == docs[0]["title"]
    assert docs[1]["topic"] == "CBE-UY 3313 Heat and Mass Tran"
    assert docs[1]["term"] == "Fall 2026"


def test_extract_rows_from_text_keeps_lettered_project_lines_in_title():
    rows = extract_rows_from_text(
        "\n".join(
            [
                "VIP-UY 300X Vertically Integrated Projects",
                "A. Concrete Canoe",
                "AB. NYU Robotic Design Team",
                "BK: Metaverse for Education",
                "School:",
                "Tandon School of Engineering",
                "Term: Fall 2026",
                "Topic: A. Concrete Canoe",
                "VIP-UY 300X | 1 - 3 units",
                "Class#: 8077",
                "Session: 1 09/02/2026 - 12/14/2026",
                "Section: A",
                "Class Status: Open",
                "Component: Project",
                "09/02/2026 - 12/14/2026 at No Room Required Room",
                "Visit the Bookstore",
            ]
        )
    )

    docs = rows_to_documents(rows, term_code="", source_url="test")

    assert docs[0]["title"] == (
        "Vertically Integrated Projects: A. Concrete Canoe; "
        "AB. NYU Robotic Design Team; BK: Metaverse for Education"
    )
    assert docs[0]["topic"] == "A. Concrete Canoe"
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
