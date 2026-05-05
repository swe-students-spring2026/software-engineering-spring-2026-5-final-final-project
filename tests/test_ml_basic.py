import os


def test_ml_src_folder_exists():
    assert os.path.isdir("ML/src")


def test_config_file_exists():
    assert os.path.isfile("ML/src/config.py")


def test_preprocess_file_exists():
    assert os.path.isfile("ML/src/preprocess.py")


def test_embedding_file_exists():
    assert os.path.isfile("ML/src/embedding.py")


def test_search_file_exists():
    assert os.path.isfile("ML/src/search.py")


def test_preprocess_file_has_pandas():
    with open("ML/src/preprocess.py", "r") as file:
        text = file.read()

    assert "pandas" in text


def test_config_has_paths():
    with open("ML/src/config.py", "r") as file:
        text = file.read()

    assert "PATH" in text