from __future__ import annotations

import re
from typing import Any

from .client import ModClient


BUILDINGS_QUERY = """
query buildings {
  buildings {
    guid
    name
    capacity
    position
    available_for
    kind
    active
    address {
      name
      postal_code
      locality
      country
      is_valid
    }
  }
}
""".strip()


EMPLOYEE_BOOKINGS_QUERY = """
query employee($guid: String!, $booking_date: [String], $active: [String]) {
  employee(guid: $guid) {
    guid
    bookings(booking_date: $booking_date, active: $active) {
      guid
      booking_date
      kind
      transport_kind
      reason
      status
      active
      building { guid name }
      floor { guid name }
      room { guid name }
      table { guid name }
      timeslot {
        guid
        timeslot_day
        timeslot_start
        timeslot_end
        kind
        sub_kind
        active
      }
    }
  }
}
""".strip()


BOOKING_CAPACITY_QUERY = """
query booking_capacity(
  $dates: [String]
  $kinds: [String]
  $subKinds: [String]
  $employeeGuid: String
) {
  booking_capacity(
    dates: $dates
    kinds: $kinds
    subKinds: $subKinds
    employee_guid: $employeeGuid
  ) {
    date
    item_kind
    item_guid
    timeslot_kind
    timeslot_sub_kind
    building_guid
    floor_guid
    room_guid
    capacity
    remaining
    favourites
    block_comment
    exception_kind
  }
}
""".strip()


BOOKING_TYPES_QUERY = """
query timeslot_kinds($active: String) {
  timeslot_kinds(active: $active) {
    guid
    name
    kind
    sub_kind
    show_capacity
    show_time
    show_capacity_in_timeslot
    can_overlap_with_booking
    can_only_select_one_per_day
    can_book_from
    can_book_until
    can_cancel_until
    active
  }
}
""".strip()


BOOKABLE_TIMESLOTS_QUERY = """
query building($kind: String, $sub_kind: String, $timeslot_day: [Int]) {
  buildings {
    guid
    name
    floors { guid name }
    timeslots_through(
      kind: $kind
      sub_kind: $sub_kind
      timeslot_day: $timeslot_day
    ) {
      guid
      timeslot_day
      timeslot_start
      timeslot_end
      capacity
      kind
      sub_kind
      active
    }
  }
  rooms {
    guid
    name
    floor {
      guid
      name
      building { guid name }
    }
    timeslots_through(
      kind: $kind
      sub_kind: $sub_kind
      timeslot_day: $timeslot_day
    ) {
      guid
      timeslot_day
      timeslot_start
      timeslot_end
      capacity
      kind
      sub_kind
      active
    }
  }
}
""".strip()


CREATE_BOOKING_MUTATION = """
mutation create_employee_booking(
  $kind: String!
  $booking_date: String!
  $building_guid: String!
  $floor_guid: String!
  $room_guid: String
  $table_guid: String
  $timeslot_guid: String!
  $employee_guid: String!
) {
  create_employee_booking(
    kind: $kind
    booking_date: $booking_date
    building_guid: $building_guid
    floor_guid: $floor_guid
    room_guid: $room_guid
    table_guid: $table_guid
    timeslot_guid: $timeslot_guid
    employee_guid: $employee_guid
  ) {
    guid
    kind
    employee { guid }
  }
}
""".strip()


def list_buildings(client: ModClient) -> Any:
    return client.graphql("buildings", BUILDINGS_QUERY)


def list_bookings(
    client: ModClient,
    employee_guid: str,
    dates: list[str] | None = None,
    *,
    include_inactive: bool = False,
) -> Any:
    variables: dict[str, Any] = {
        "guid": employee_guid,
        "booking_date": dates,
        "active": None if include_inactive else ["yes"],
    }
    return client.graphql("bookings", EMPLOYEE_BOOKINGS_QUERY, variables)


def get_availability(
    client: ModClient,
    employee_guid: str,
    dates: list[str],
    *,
    kinds: list[str] | None = None,
    sub_kinds: list[str] | None = None,
) -> Any:
    variables: dict[str, Any] = {
        "dates": dates,
        "kinds": kinds,
        "subKinds": sub_kinds,
        "employeeGuid": employee_guid,
    }
    return client.graphql("booking_capacity", BOOKING_CAPACITY_QUERY, variables)


def list_booking_types(client: ModClient, *, include_inactive: bool = False) -> Any:
    active = None if include_inactive else "yes"
    return client.graphql("timeslot_kinds", BOOKING_TYPES_QUERY, {"active": active})


def booking_type_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


def resolve_booking_type(result: Any, requested: str) -> tuple[str, str]:
    items = result.get("timeslot_kinds", []) if isinstance(result, dict) else []
    requested_normalized = requested.strip().lower()
    requested_slug = booking_type_slug(requested)
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if requested_normalized in {name.lower(), booking_type_slug(name)} or requested_slug == booking_type_slug(name):
            kind = item.get("kind")
            sub_kind = item.get("sub_kind")
            if isinstance(kind, str) and isinstance(sub_kind, str):
                return kind, sub_kind
    available = ", ".join(
        str(item.get("name", "")).strip()
        for item in items
        if isinstance(item, dict) and item.get("name")
    )
    raise ValueError(f"Unknown booking type '{requested}'. Available types: {available}")


def list_bookable_timeslots(
    client: ModClient, kind: str, sub_kind: str, timeslot_day: int
) -> Any:
    return client.graphql(
        "bookable_timeslots",
        BOOKABLE_TIMESLOTS_QUERY,
        {"kind": kind, "sub_kind": sub_kind, "timeslot_day": [timeslot_day]},
    )


def create_booking(
    client: ModClient,
    *,
    employee_guid: str,
    booking_date: str,
    kind: str,
    building_guid: str,
    floor_guid: str,
    timeslot_guid: str,
    room_guid: str | None = None,
) -> Any:
    return client.graphql(
        "create_employee_booking",
        CREATE_BOOKING_MUTATION,
        {
            "kind": kind,
            "booking_date": booking_date,
            "building_guid": building_guid,
            "floor_guid": floor_guid,
            "room_guid": room_guid,
            "table_guid": None,
            "timeslot_guid": timeslot_guid,
            "employee_guid": employee_guid,
        },
    )
