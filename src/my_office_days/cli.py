from __future__ import annotations

import json
from datetime import date as Date
from typing import Annotated

import typer

from . import __version__
from .auth import (
    delete_encryption_key,
    delete_token,
    get_encryption_key,
    get_token,
    set_encryption_key,
    set_token,
)
from .client import ModApiError, ModClient
from .config import Config, data_dir
from .operations import (
    get_availability,
    booking_type_slug,
    create_booking,
    list_booking_types,
    list_bookable_timeslots,
    list_bookings,
    list_buildings,
    resolve_booking_type,
)

app = typer.Typer(help="Manage your personal My Office Days account.", no_args_is_help=True)
config_app = typer.Typer(help="Manage local configuration.")
auth_app = typer.Typer(help="Manage local authentication.")
api_app = typer.Typer(help="Inspect confirmed API endpoints.")
booking_app = typer.Typer(help="View your bookings.")
app.add_typer(config_app, name="config")
app.add_typer(auth_app, name="auth")
app.add_typer(api_app, name="api")
app.add_typer(booking_app, name="bookings")


def _version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version, is_eager=True),
    ] = None,
) -> None:
    """My Office Days CLI."""


@app.command()
def doctor() -> None:
    """Check whether configuration and authentication are ready."""
    config = Config.load()
    checks = {
        "data_dir": str(data_dir()),
        "base_url_configured": bool(config.base_url),
        "token_available": bool(get_token()),
        "encryption_key_available": bool(get_encryption_key()),
        "employee_guid_configured": bool(config.employee_guid),
        "api_contract_known": True,
    }
    typer.echo(json.dumps(checks, indent=2))
    if not config.base_url:
        typer.echo("Next step: configure the confirmed API base URL.", err=True)


@config_app.command("set-base-url")
def config_set_base_url(base_url: str) -> None:
    """Store the confirmed API base URL locally."""
    if not base_url.startswith("https://"):
        raise typer.BadParameter("Use an https:// URL.")
    config = Config.load()
    config.base_url = base_url.rstrip("/")
    path = config.save()
    typer.echo(f"Saved to {path}")


@config_app.command("set-employee-guid")
def config_set_employee_guid(employee_guid: str) -> None:
    """Store your employee GUID locally."""
    employee_guid = employee_guid.strip()
    if not employee_guid:
        raise typer.BadParameter("Employee GUID cannot be empty.")
    config = Config.load()
    config.employee_guid = employee_guid
    path = config.save()
    typer.echo(f"Saved to {path}")


@config_app.command("show")
def config_show() -> None:
    """Show non-secret configuration."""
    config = Config.load()
    typer.echo(
        json.dumps(
            {"base_url": config.base_url, "employee_guid": config.employee_guid},
            indent=2,
        )
    )


@auth_app.command("set-token")
def auth_set_token() -> None:
    """Store the employee session in the OS keyring."""
    token = typer.prompt("Employee session", hide_input=True).strip()
    if not token:
        raise typer.BadParameter("Token cannot be empty.")
    set_token(token)
    typer.echo("Token stored securely in the OS keyring.")


@auth_app.command("login")
def auth_login() -> None:
    """Log in with the one-time code sent by My Office Days."""
    config = Config.load()
    if not config.base_url:
        typer.echo("Configure the API base URL first.", err=True)
        raise typer.Exit(2)

    email = typer.prompt("Email address").strip().lower()
    if not email or "@" not in email:
        raise typer.BadParameter("Enter a valid email address.")

    try:
        with ModClient(config.base_url) as client:
            client.request_login_token(email)
            typer.echo("A one-time login code has been sent.")
            code = typer.prompt("6-digit code", hide_input=True).strip()
            if len(code) != 6 or not code.isdigit():
                raise typer.BadParameter("The login code must contain 6 digits.")
            result = client.authenticate(email, code)
    except ModApiError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error

    guid = result.get("guid")
    session = result.get("authorisation")
    encryption_key = result.get("key")
    if not isinstance(guid, str) or not guid or not isinstance(session, str) or not session:
        typer.echo("The login response is missing required account data.", err=True)
        raise typer.Exit(1)
    if encryption_key is not None and not isinstance(encryption_key, str):
        typer.echo("The login response contains an unknown key format.", err=True)
        raise typer.Exit(1)

    config.employee_guid = guid
    config.save()
    set_token(session)
    if encryption_key:
        set_encryption_key(encryption_key)
    else:
        delete_encryption_key()
    typer.echo("Logged in; account credentials were stored securely.")


@auth_app.command("status")
def auth_status() -> None:
    """Check whether credentials are available without displaying them."""
    typer.echo(
        json.dumps(
            {
                "token_available": bool(get_token()),
                "encryption_key_available": bool(get_encryption_key()),
            },
            indent=2,
        )
    )


@auth_app.command("logout")
def auth_logout() -> None:
    """Remove authentication secrets from the OS keyring."""
    removed = delete_token()
    removed = delete_encryption_key() or removed
    typer.echo("Authentication removed." if removed else "No stored authentication found.")


@api_app.command("get")
def api_get(path: str) -> None:
    """Call a confirmed read-only API path and print JSON."""
    config = Config.load()
    if not config.base_url:
        typer.echo("Configure the API base URL first.", err=True)
        raise typer.Exit(2)
    try:
        with ModClient(config.base_url, get_token()) as client:
            result = client.get(path)
    except ModApiError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


def _configured_client(config: Config) -> ModClient:
    if not config.base_url:
        typer.echo("Configure the API base URL first.", err=True)
        raise typer.Exit(2)
    token = get_token()
    if not token:
        typer.echo("Log in first with 'mod auth login'.", err=True)
        raise typer.Exit(2)
    return ModClient(config.base_url, token, get_encryption_key())


@app.command("buildings")
def buildings() -> None:
    """View available buildings."""
    try:
        with _configured_client(Config.load()) as client:
            result = list_buildings(client)
    except ModApiError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("booking-types")
def booking_types(
    include_inactive: Annotated[
        bool,
        typer.Option(help="Include inactive booking types."),
    ] = False,
) -> None:
    """List available booking types and their kind/sub-kind values."""
    try:
        with _configured_client(Config.load()) as client:
            result = list_booking_types(client, include_inactive=include_inactive)
    except ModApiError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    if isinstance(result, dict) and isinstance(result.get("timeslot_kinds"), list):
        result = {
            "booking_types": [
                {
                    "name": item.get("name", "").strip(),
                    "type": booking_type_slug(str(item.get("name", ""))),
                    "shows_capacity": item.get("show_capacity") == "yes",
                    "shows_time": item.get("show_time") == "yes",
                    "can_only_select_one_per_day": item.get("can_only_select_one_per_day") == "yes",
                    "active": item.get("active") == "yes",
                }
                for item in result["timeslot_kinds"]
                if isinstance(item, dict)
            ]
        }
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("availability")
def availability(
    date: Annotated[
        list[str],
        typer.Option("--date", "-d", help="Date as YYYY-MM-DD; repeatable."),
    ],
    booking_type: Annotated[
        str | None,
        typer.Option(
            "--type",
            "-t",
            help="Friendly booking type name, for example 'Sport session'.",
        ),
    ] = None,
    kind: Annotated[
        list[str] | None,
        typer.Option("--kind", "-k", help="Advanced: technical booking kind; repeatable."),
    ] = None,
    sub_kind: Annotated[
        list[str] | None,
        typer.Option("--sub-kind", help="Advanced: technical booking sub-kind; repeatable."),
    ] = None,
) -> None:
    """View booking capacity and remaining availability for one or more dates."""
    if not date:
        raise typer.BadParameter("Provide at least one date.", param_hint="--date")
    for value in date:
        try:
            Date.fromisoformat(value)
        except ValueError as error:
            raise typer.BadParameter(
                f"Invalid date '{value}'; use YYYY-MM-DD.", param_hint="--date"
            ) from error

    if booking_type and (kind or sub_kind):
        raise typer.BadParameter(
            "Use either --type or the advanced --kind/--sub-kind filters, not both."
        )

    config = Config.load()
    if not config.employee_guid:
        typer.echo("Configure your employee GUID first.", err=True)
        raise typer.Exit(2)
    try:
        with _configured_client(config) as client:
            if booking_type:
                try:
                    resolved_kind, resolved_sub_kind = resolve_booking_type(
                        list_booking_types(client), booking_type
                    )
                except ValueError as error:
                    raise typer.BadParameter(str(error), param_hint="--type") from error
                kind = [resolved_kind]
                sub_kind = [resolved_sub_kind]
            result = get_availability(
                client,
                config.employee_guid,
                date,
                kinds=kind,
                sub_kinds=sub_kind,
            )
    except ModApiError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@booking_app.command("create")
def bookings_create(
    date: Annotated[str, typer.Option("--date", "-d", help="Date as YYYY-MM-DD.")],
    booking_type: Annotated[
        str,
        typer.Option("--type", "-t", help="Booking type, for example 'Sport session'."),
    ],
    timeslot: Annotated[
        str | None,
        typer.Option("--timeslot", help="Timeslot GUID; required if multiple slots match."),
    ] = None,
    slot: Annotated[
        str | None,
        typer.Option(
            "--slot",
            help="Select 'early' or 'late' when multiple timeslots match.",
        ),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip the confirmation prompt."),
    ] = False,
) -> None:
    """Create one booking after showing and confirming the exact plan."""
    try:
        parsed_date = Date.fromisoformat(date)
    except ValueError as error:
        raise typer.BadParameter(
            f"Invalid date '{date}'; use YYYY-MM-DD.", param_hint="--date"
        ) from error
    if slot not in (None, "early", "late"):
        raise typer.BadParameter("Use 'early' or 'late'.", param_hint="--slot")
    if slot and timeslot:
        raise typer.BadParameter("Use either --slot or --timeslot, not both.")

    config = Config.load()
    if not config.employee_guid:
        typer.echo("Configure your employee GUID first.", err=True)
        raise typer.Exit(2)

    try:
        with _configured_client(config) as client:
            type_result = list_booking_types(client)
            try:
                kind, sub_kind = resolve_booking_type(type_result, booking_type)
            except ValueError as error:
                raise typer.BadParameter(str(error), param_hint="--type") from error

            slots_result = list_bookable_timeslots(
                client, kind, sub_kind, parsed_date.isoweekday()
            )
            candidates: list[dict[str, object]] = []
            for building in slots_result.get("buildings", []):
                if not isinstance(building, dict):
                    continue
                floors = building.get("floors") or []
                floor_guid = ""
                if len(floors) == 1 and isinstance(floors[0], dict):
                    floor_guid = str(floors[0].get("guid") or "")
                for slot in building.get("timeslots_through") or []:
                    if not isinstance(slot, dict) or slot.get("active") != "yes":
                        continue
                    candidates.append(
                        {
                            "building_guid": building.get("guid"),
                            "building": building.get("name"),
                            "floor_guid": floor_guid,
                            "room_guid": None,
                            "room": None,
                            "timeslot_guid": slot.get("guid"),
                            "start": slot.get("timeslot_start"),
                            "end": slot.get("timeslot_end"),
                            "capacity": slot.get("capacity"),
                        }
                    )

            for room in slots_result.get("rooms", []):
                if not isinstance(room, dict):
                    continue
                floor = room.get("floor") or {}
                building = floor.get("building") or {} if isinstance(floor, dict) else {}
                for room_slot in room.get("timeslots_through") or []:
                    if not isinstance(room_slot, dict) or room_slot.get("active") != "yes":
                        continue
                    candidates.append(
                        {
                            "building_guid": building.get("guid"),
                            "building": building.get("name"),
                            "floor_guid": floor.get("guid") if isinstance(floor, dict) else None,
                            "room_guid": room.get("guid"),
                            "room": room.get("name"),
                            "timeslot_guid": room_slot.get("guid"),
                            "start": room_slot.get("timeslot_start"),
                            "end": room_slot.get("timeslot_end"),
                            "capacity": room_slot.get("capacity"),
                        }
                    )

            if timeslot:
                candidates = [item for item in candidates if item["timeslot_guid"] == timeslot]
            candidates.sort(key=lambda item: str(item.get("start") or ""))
            if slot == "early" and candidates:
                candidates = [candidates[0]]
            elif slot == "late" and candidates:
                candidates = [candidates[-1]]
            if not candidates:
                typer.echo("No matching active timeslot was found.", err=True)
                raise typer.Exit(2)
            if len(candidates) > 1:
                typer.echo(json.dumps({"matching_timeslots": candidates}, indent=2))
                typer.echo("Choose one with --timeslot <GUID>.", err=True)
                raise typer.Exit(2)

            selected = candidates[0]
            capacity_result = get_availability(
                client,
                config.employee_guid,
                [date],
                kinds=[kind],
                sub_kinds=[sub_kind],
            )
            capacity_items = capacity_result.get("booking_capacity", [])
            matching_capacity = [
                item
                for item in capacity_items
                if isinstance(item, dict)
                and item.get("building_guid") == selected["building_guid"]
            ]
            if not matching_capacity:
                typer.echo("No current capacity information was found for this timeslot.", err=True)
                raise typer.Exit(2)
            remaining = min(
                int(item.get("remaining", 0)) for item in matching_capacity
            )
            if remaining < 1:
                typer.echo("This booking type is no longer available on that date.", err=True)
                raise typer.Exit(2)

            before = list_bookings(client, config.employee_guid, [date])
            existing = before.get("employee", {}).get("bookings", [])
            if any(
                item.get("timeslot", {}).get("guid") == selected["timeslot_guid"]
                and item.get("active") == "yes"
                for item in existing
                if isinstance(item, dict)
            ):
                typer.echo("This timeslot is already booked.", err=True)
                raise typer.Exit(2)

            plan = {
                "action": "create booking",
                "date": date,
                "type": booking_type.strip(),
                "location": selected["building"],
                "room": selected["room"],
                "start": selected["start"],
                "end": selected["end"],
                "capacity": selected["capacity"],
                "remaining_before_booking": remaining,
            }
            typer.echo(json.dumps({"plan": plan}, indent=2, ensure_ascii=False))
            if not yes and not typer.confirm("Create this booking?"):
                typer.echo("Booking cancelled; no changes were made.")
                raise typer.Exit()

            result = create_booking(
                client,
                employee_guid=config.employee_guid,
                booking_date=date,
                kind=kind,
                building_guid=str(selected["building_guid"]),
                floor_guid=str(selected["floor_guid"]),
                timeslot_guid=str(selected["timeslot_guid"]),
                room_guid=(str(selected["room_guid"]) if selected["room_guid"] else None),
            )
            after = list_bookings(client, config.employee_guid, [date])
            capacity_after_result = get_availability(
                client,
                config.employee_guid,
                [date],
                kinds=[kind],
                sub_kinds=[sub_kind],
            )
    except ModApiError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error

    created = result.get("create_employee_booking", {})
    created_guid = created.get("guid") if isinstance(created, dict) else None
    verified = any(
        item.get("guid") == created_guid and item.get("active") == "yes"
        for item in after.get("employee", {}).get("bookings", [])
        if isinstance(item, dict)
    )
    if not created_guid or not verified:
        typer.echo("The server response could not be verified by reading the booking back.", err=True)
        raise typer.Exit(1)
    matching_capacity_after = [
        item
        for item in capacity_after_result.get("booking_capacity", [])
        if isinstance(item, dict)
        and item.get("building_guid") == selected["building_guid"]
        and (not selected["room_guid"] or item.get("room_guid") == selected["room_guid"])
    ]
    remaining_after = (
        min(int(item.get("remaining", 0)) for item in matching_capacity_after)
        if matching_capacity_after
        else None
    )
    typer.echo(
        json.dumps(
            {
                "created": True,
                "verified": True,
                "booking": plan,
                "remaining_after_booking": remaining_after,
            },
            indent=2,
        )
    )


@booking_app.command("list")
def bookings_list(
    date: Annotated[
        list[str] | None,
        typer.Option("--date", "-d", help="Date as YYYY-MM-DD; repeatable."),
    ] = None,
    include_inactive: Annotated[
        bool,
        typer.Option(help="Include cancelled and inactive bookings."),
    ] = False,
) -> None:
    """View your active bookings, optionally for specific dates."""
    for value in date or []:
        try:
            Date.fromisoformat(value)
        except ValueError as error:
            raise typer.BadParameter(
                f"Invalid date '{value}'; use YYYY-MM-DD.", param_hint="--date"
            ) from error
    config = Config.load()
    if not config.employee_guid:
        typer.echo("Configure your employee GUID first.", err=True)
        raise typer.Exit(2)
    try:
        with _configured_client(config) as client:
            result = list_bookings(
                client,
                config.employee_guid,
                date,
                include_inactive=include_inactive,
            )
    except ModApiError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
