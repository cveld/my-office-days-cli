---
name: my-office-days
description: Manage the user's personal My Office Days account through the secure my-office-days-cli package. Use this skill whenever the user mentions My Office Days, office days, workplace or parking availability, their bookings, or asks to book a supported workplace service. Use the CLI for account setup, login, buildings, booking types, availability, and bookings; require a concrete plan and explicit confirmation before creating a booking.
compatibility: Requires Python 3.11+ and uv. Authentication uses the operating-system keyring.
metadata:
  author: cveld
  version: "0.1.0"
---

# My Office Days

Use the published CLI through `uvx`. Do not automate the website or construct
unconfirmed API calls.

## Safety rules

- Operate only on the user's own authorized account.
- Never print, request for chat, persist, or expose sessions, encryption keys,
  cookies, one-time codes, or other credentials.
- Treat booking details and availability as potentially personal information;
  return only what the user needs.
- Before creating a booking, show the exact action, date, booking type,
  location, room when applicable, and timeslot. Obtain explicit confirmation.
- Do not pass `--yes` unless the user has already confirmed that exact plan in
  the conversation. Otherwise, let the CLI ask interactively.
- Never guess a mutation, endpoint, technical booking type, or timeslot.
- Cancellation is not supported. Explain this rather than attempting an API
  call or another workaround.

## Check the installation and account

Run:

```powershell
uvx my-office-days-cli --version
uvx my-office-days-cli doctor
```

If configuration is missing, ask the user for their confirmed tenant base URL.
It must be an HTTPS URL and may include a customer path:

```powershell
uvx my-office-days-cli config set-base-url https://<tenant-host>/<customer-path>
```

If authentication is missing, start the passwordless login flow:

```powershell
uvx my-office-days-cli auth login
```

The user enters their email address and one-time code directly into the CLI.
Do not ask them to paste either value into the conversation. The resulting
session and encryption key are stored in the operating-system keyring.

## Read account information

Discover the organization's configured locations and friendly booking types
instead of assuming them:

```powershell
uvx my-office-days-cli buildings
uvx my-office-days-cli booking-types
```

Check availability for one or more concrete dates:

```powershell
uvx my-office-days-cli availability --date 2026-10-15 --type "Lunch"
uvx my-office-days-cli availability --date 2026-10-15 --date 2026-10-16 --type "Sport session"
```

List the user's bookings, optionally for a date:

```powershell
uvx my-office-days-cli bookings list
uvx my-office-days-cli bookings list --date 2026-10-15
```

Use ISO dates (`YYYY-MM-DD`) in commands. If the user gives a relative date,
resolve it against today's date and state the resulting date explicitly.

## Create a booking

First inspect booking types and availability. Then run the create command
without `--yes` so the CLI can resolve available timeslots and display its
read-before-write plan:

```powershell
uvx my-office-days-cli bookings create --date 2026-10-15 --type "Lunch" --slot early
```

When several timeslots match, present the choices returned by the CLI and ask
the user to select one. Use `--slot early`, `--slot late`, or the exact
`--timeslot <GUID>` returned by the CLI; never invent a GUID.

After confirmation, perform one mutation only. Report the CLI's read-back
verification, including whether the booking exists and the updated remaining
capacity. If verification fails, say so clearly and do not retry automatically.

## Errors and unsupported requests

- For missing configuration or authentication, guide the user through the
  setup commands above.
- For unknown booking types, run `booking-types` and offer the returned names.
- For unavailable capacity, report it and ask whether the user wants another
  date or supported timeslot.
- For cancellation or any unsupported mutation, stop safely and explain that
  the CLI does not yet implement a validated contract for that operation.
