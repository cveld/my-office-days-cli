import httpx
import respx

from my_office_days import cli
from my_office_days.client import ModClient

SELECTED = {
    "building_guid": "building-1",
    "floor_guid": "floor-1",
    "room_guid": "room-1",
    "timeslot_guid": "slot-early",
    "start": "11:45:00",
    "end": "12:30:00",
}


@respx.mock
def test_remaining_is_asked_for_exactly_the_selected_slot():
    route = respx.post("https://tenant.example/connection/graphql").mock(
        return_value=httpx.Response(
            200,
            json={
                "timeslot_capacity": {
                    "data": {
                        "timeslot_capacity": {
                            "timeslot_guid": "slot-early",
                            "capacity": 75,
                            "remaining": 2,
                            "exception_kind": None,
                        }
                    }
                }
            },
        )
    )

    with ModClient("https://tenant.example", "session") as client:
        remaining = cli._selected_slot_remaining(client, SELECTED, "2026-11-26", "lunch")

    assert remaining == 2
    body = __import__("json").loads(route.calls[0].request.content)
    assert body[0]["name"] == "timeslot_capacity"
    assert body[0]["variables"] == {
        "booking_date": "2026-11-26",
        "kind": "lunch",
        "building_guid": "building-1",
        "floor_guid": "floor-1",
        "room_guid": "room-1",
        "timeslot_guid": "slot-early",
    }


@respx.mock
def test_full_slot_reports_zero_remaining():
    respx.post("https://tenant.example/connection/graphql").mock(
        return_value=httpx.Response(
            200,
            json={
                "timeslot_capacity": {
                    "data": {
                        "timeslot_capacity": {
                            "capacity": 25,
                            "remaining": 0,
                            "exception_kind": "increase",
                        }
                    }
                }
            },
        )
    )

    with ModClient("https://tenant.example", "session") as client:
        assert cli._selected_slot_remaining(client, SELECTED, "2026-11-26", "lunch") == 0


@respx.mock
def test_missing_capacity_is_unknown_not_zero():
    respx.post("https://tenant.example/connection/graphql").mock(
        return_value=httpx.Response(
            200, json={"timeslot_capacity": {"data": {"timeslot_capacity": None}}}
        )
    )

    with ModClient("https://tenant.example", "session") as client:
        assert cli._selected_slot_remaining(client, SELECTED, "2026-11-26", "lunch") is None


def test_slot_label_shows_start_and_end_without_seconds():
    assert cli._slot_label(SELECTED) == "11:45-12:30"
