"""Tests for teacher-created public and private fish ponds."""


def test_private_pond_requires_room_code_before_channel_is_visible(client):
    """Private ponds stay hidden until a kitten joins by room code."""

    create_response = client.post(
        "/ponds",
        json={
            "cat_id": "cat_1",
            "name": "Hidden Pond",
            "visibility": "private",
            "room_code": "abc123",
        },
    )
    assert create_response.status_code == 200
    pond = create_response.json()

    channels_before = client.get("/quiz/channels/kitten_1")
    assert channels_before.status_code == 200
    assert channels_before.json()["private"] == []

    join_response = client.post(
        "/ponds/private/join",
        json={"user_id": "kitten_1", "room_code": "ABC123"},
    )
    assert join_response.status_code == 200
    assert join_response.json()["pond_id"] == pond["pond_id"]

    channels_after = client.get("/quiz/channels/kitten_1")
    assert channels_after.status_code == 200
    private_channels = channels_after.json()["private"]
    assert [channel["pond_id"] for channel in private_channels] == [pond["pond_id"]]


def test_teacher_ponds_can_be_listed_with_their_problems(client):
    """Teacher-created ponds expose their problem lists."""

    create_response = client.post(
        "/ponds",
        json={"cat_id": "cat_2", "name": "Loops Pond", "visibility": "public"},
    )
    assert create_response.status_code == 200
    pond = create_response.json()

    problem_response = client.post(
        f"/ponds/{pond['pond_id']}/problems",
        json={
            "cat_id": "cat_2",
            "pond_id": pond["pond_id"],
            "title": "Double a number",
            "prompt": "Write solve(n) and return n * 2.",
            "starter_code": "def solve(n):\n    pass\n",
            "reference_solution": "def solve(n):\n    return n * 2\n",
            "test_code": "assert solve(3) == 6\n",
            "topic": "arithmetic",
        },
    )
    assert problem_response.status_code == 200

    teacher_ponds = client.get("/ponds/teacher/cat_2")
    assert teacher_ponds.status_code == 200
    assert teacher_ponds.json()[0]["pond_id"] == pond["pond_id"]

    pond_problems = client.get(f"/ponds/{pond['pond_id']}/problems")
    assert pond_problems.status_code == 200
    assert pond_problems.json()[0]["title"] == "Double a number"


def test_teacher_can_edit_and_delete_pond_problem(client):
    """Teacher-owned problems can be updated and removed from a pond."""

    create_response = client.post(
        "/ponds",
        json={"cat_id": "cat_3", "name": "Editable Pond", "visibility": "private"},
    )
    assert create_response.status_code == 200
    pond = create_response.json()

    problem_response = client.post(
        f"/ponds/{pond['pond_id']}/problems",
        json={
            "cat_id": "cat_3",
            "pond_id": pond["pond_id"],
            "title": "Old title",
            "prompt": "Write solve(n).",
            "starter_code": "def solve(n):\n    pass\n",
            "reference_solution": "def solve(n):\n    return n\n",
            "test_code": "assert solve(1) == 1\n",
            "topic": "identity",
        },
    )
    assert problem_response.status_code == 200
    problem_id = problem_response.json()["problem"]["id"]

    update_response = client.put(
        f"/ponds/{pond['pond_id']}/problems/{problem_id}",
        json={
            "cat_id": "cat_3",
            "title": "New title",
            "prompt": "Write solve(n) and return n + 1.",
            "starter_code": "def solve(n):\n    pass\n",
            "reference_solution": "def solve(n):\n    return n + 1\n",
            "test_code": "assert solve(1) == 2\n",
            "topic": "arithmetic",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["problem"]["title"] == "New title"

    pond_problems = client.get(f"/ponds/{pond['pond_id']}/problems")
    assert pond_problems.status_code == 200
    assert pond_problems.json()[0]["instructions"] == "Write solve(n) and return n + 1."

    delete_response = client.delete(
        f"/ponds/{pond['pond_id']}/problems/{problem_id}?cat_id=cat_3"
    )
    assert delete_response.status_code == 200

    empty_problems = client.get(f"/ponds/{pond['pond_id']}/problems")
    assert empty_problems.status_code == 200
    assert empty_problems.json() == []
