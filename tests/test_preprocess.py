import pandas as pd


def test_cleaning_steps_basic():
    data = pd.DataFrame({
        "Created Date": [" 2026-04-28 "],
        "Problem": [" Noise "],
        "Problem Detail": [" Loud music "],
        "Longitude": ["-73.9857"],
        "Latitude": ["40.7484"],
    })

    data["Created Date"] = data["Created Date"].astype("string").str.strip()
    data["Problem"] = data["Problem"].astype("string").str.strip()
    data["Problem Detail"] = data["Problem Detail"].astype("string").str.strip()
    data["Longitude"] = pd.to_numeric(data["Longitude"], errors="coerce")
    data["Latitude"] = pd.to_numeric(data["Latitude"], errors="coerce")

    assert data.loc[0, "Created Date"] == "2026-04-28"
    assert data.loc[0, "Problem"] == "Noise"
    assert data.loc[0, "Problem Detail"] == "Loud music"
    assert data.loc[0, "Longitude"] == -73.9857
    assert data.loc[0, "Latitude"] == 40.7484


def test_drop_missing_rows():
    data = pd.DataFrame({
        "Created Date": ["2026-04-28", None],
        "Problem": ["Noise", "Parking"],
        "Problem Detail": ["Loud music", "Blocked driveway"],
        "Longitude": [-73.9857, -73.9000],
        "Latitude": [40.7484, 40.7000],
    })

    cleaned = data.dropna()

    assert len(cleaned) == 1
    assert cleaned.iloc[0]["Problem"] == "Noise"


def test_bad_coordinates_become_missing():
    data = pd.DataFrame({
        "Longitude": ["not a number"],
        "Latitude": ["40.7484"],
    })

    data["Longitude"] = pd.to_numeric(data["Longitude"], errors="coerce")
    data["Latitude"] = pd.to_numeric(data["Latitude"], errors="coerce")

    assert pd.isna(data.loc[0, "Longitude"])
    assert data.loc[0, "Latitude"] == 40.7484