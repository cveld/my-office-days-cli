import httpx
import respx

from my_office_days.client import ModClient
from my_office_days.operations import (
    get_availability,
    booking_type_slug,
    create_booking,
    list_booking_types,
    list_bookable_timeslots,
    list_bookings,
    list_buildings,
    resolve_booking_type,
)


@respx.mock
def test_list_buildings_uses_confirmed_operation():
    route = respx.post("https://tenant.example/connection/graphql").mock(
        return_value=httpx.Response(
            200, json={"buildings": {"data": {"buildings": []}}}
        )
    )

    with ModClient("https://tenant.example", "session") as client:
        assert list_buildings(client) == {"buildings": []}

    request = route.calls[0].request
    assert b"query buildings" in request.content


@respx.mock
def test_list_bookings_passes_employee_and_date_filters():
    route = respx.post("https://tenant.example/connection/graphql").mock(
        return_value=httpx.Response(
            200,
            json={"bookings": {"data": {"employee": {"bookings": []}}}},
        )
    )

    with ModClient("https://tenant.example", "session") as client:
        result = list_bookings(client, "employee-1", ["2026-10-12"])

    assert result == {"employee": {"bookings": []}}
    body = __import__("json").loads(route.calls[0].request.content)
    assert body[0]["variables"] == {
        "guid": "employee-1",
        "booking_date": ["2026-10-12"],
        "active": ["yes"],
    }


@respx.mock
def test_availability_passes_confirmed_capacity_filters():
    route = respx.post("https://tenant.example/connection/graphql").mock(
        return_value=httpx.Response(
            200,
            json={
                "booking_capacity": {
                    "data": {"booking_capacity": [{"date": "2026-10-15", "remaining": 4}]}
                }
            },
        )
    )

    with ModClient("https://tenant.example", "session") as client:
        result = get_availability(
            client,
            "employee-1",
            ["2026-10-15"],
            kinds=["booking"],
        )

    assert result["booking_capacity"][0]["remaining"] == 4
    body = __import__("json").loads(route.calls[0].request.content)
    assert body[0]["name"] == "booking_capacity"
    assert body[0]["variables"] == {
        "dates": ["2026-10-15"],
        "kinds": ["booking"],
        "subKinds": None,
        "employeeGuid": "employee-1",
    }


@respx.mock
def test_list_booking_types_filters_active_types():
    route = respx.post("https://tenant.example/connection/graphql").mock(
        return_value=httpx.Response(
            200,
            json={
                "timeslot_kinds": {
                    "data": {
                        "timeslot_kinds": [
                            {"name": "Sport session", "kind": "custom", "sub_kind": "custom_1"}
                        ]
                    }
                }
            },
        )
    )

    with ModClient("https://tenant.example", "session") as client:
        result = list_booking_types(client)

    assert result["timeslot_kinds"][0]["sub_kind"] == "custom_1"
    body = __import__("json").loads(route.calls[0].request.content)
    assert body[0]["name"] == "timeslot_kinds"
    assert body[0]["variables"] == {"active": "yes"}


def test_resolve_booking_type_uses_friendly_name_or_slug():
    result = {
        "timeslot_kinds": [
            {"name": "Sport session ", "kind": "custom", "sub_kind": "custom_1"}
        ]
    }

    assert booking_type_slug("Sport session ") == "sport-session"
    assert resolve_booking_type(result, "Sport session") == ("custom", "custom_1")
    assert resolve_booking_type(result, "sport-session") == ("custom", "custom_1")


@respx.mock
def test_create_booking_uses_confirmed_mutation_fields():
    route = respx.post("https://tenant.example/connection/graphql").mock(
        return_value=httpx.Response(
            200,
            json={
                "create_employee_booking": {
                    "data": {"create_employee_booking": {"guid": "booking-1", "kind": "custom"}}
                }
            },
        )
    )
    with ModClient("https://tenant.example", "session") as client:
        result = create_booking(
            client,
            employee_guid="employee-1",
            booking_date="2026-10-12",
            kind="custom",
            building_guid="building-1",
            floor_guid="",
            timeslot_guid="timeslot-1",
            room_guid="room-1",
        )
    assert result["create_employee_booking"]["guid"] == "booking-1"
    body = __import__("json").loads(route.calls[0].request.content)
    assert body[0]["variables"]["floor_guid"] == ""
    assert body[0]["variables"]["room_guid"] == "room-1"
    assert body[0]["variables"]["timeslot_guid"] == "timeslot-1"


@respx.mock
def test_list_bookable_timeslots_filters_type_and_weekday():
    route = respx.post("https://tenant.example/connection/graphql").mock(
        return_value=httpx.Response(200, json={"bookable_timeslots": {"data": {"buildings": []}}})
    )
    with ModClient("https://tenant.example", "session") as client:
        assert list_bookable_timeslots(client, "custom", "custom_1", 1) == {"buildings": []}
    body = __import__("json").loads(route.calls[0].request.content)
    assert body[0]["variables"] == {
        "kind": "custom",
        "sub_kind": "custom_1",
        "timeslot_day": [1],
    }
