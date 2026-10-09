# My Office Days CLI

[![CI](https://github.com/cveld/my-office-days-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/cveld/my-office-days-cli/actions/workflows/ci.yml)
[![Release Please](https://github.com/cveld/my-office-days-cli/actions/workflows/release-please.yml/badge.svg)](https://github.com/cveld/my-office-days-cli/actions/workflows/release-please.yml)
[![PyPI](https://img.shields.io/pypi/v/my-office-days-cli)](https://pypi.org/project/my-office-days-cli/)
[![Python](https://img.shields.io/pypi/pyversions/my-office-days-cli)](https://pypi.org/project/my-office-days-cli/)

A secure command-line client for your personal **My Office Days** account. View
locations and availability, inspect your bookings, and create a booking with an
explicit confirmation and read-back verification.

The API behavior implemented by this project was derived from the official
[My office days Android app on Google Play](https://play.google.com/store/apps/details?id=nl.ondmand.myofficedays&hl=en_US).

> [!IMPORTANT]
> This is an independent community project. It is not affiliated with or
> endorsed by My Office Days or On-D-Mand.

## Highlights

- Passwordless login with the official one-time email-code flow.
- Sessions and encryption keys stay in the operating-system keyring.
- Supports the encrypted transport used by production tenants.
- Friendly booking type names such as `Lunch` and `Sport session`.
- Every booking shows a concrete plan and requires confirmation.
- JSON output makes the CLI convenient for scripts and agents.

## Requirements

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- Your own authorized My Office Days account

## Run without installing

After the first package has been published to PyPI:

```powershell
uvx --from my-office-days-cli mod --help
```

You can also install the command into a persistent uv tool environment:

```powershell
uv tool install my-office-days-cli
mod --help
```

## Configure and log in

The base URL includes both the tenant host and customer path:

```powershell
mod config set-base-url https://<tenant>.server.werktopkantoor.nl/<customer-id>
mod auth login
mod doctor
```

`auth login` asks for your email address and a six-digit code. The email address
and code are not stored. The resulting session and optional encryption key are
saved in the OS keyring. Non-secret configuration is stored under
`%LOCALAPPDATA%\my-office-days-cli` on Windows.

## Common commands

List the booking types configured by your organization:

```powershell
mod booking-types
```

Check availability using a friendly booking type:

```powershell
mod availability --date 2026-10-15 --type Lunch
mod availability --date 2026-10-12 --type "Sport session"
```

List your bookings:

```powershell
mod bookings list
mod bookings list --date 2026-10-15
```

Create a booking:

```powershell
mod bookings create --date 2026-10-15 --type Lunch --slot early
```

The CLI first checks the current state and prints the exact date, location,
timeslot, capacity, and remaining places. Nothing changes until you confirm.
Use `--yes` only when you have already reviewed that plan.

## Security model

- Only use the CLI for an account you are authorized to access.
- Credentials never belong in config files, command output, or Git.
- Booking creation performs a read-before-write and read-back verification.
- Unknown mutation contracts fail closed rather than guessing against
  production.

See [`docs/security.md`](docs/security.md) for details.

## Development

```powershell
git clone https://github.com/cveld/my-office-days-cli.git
cd my-office-days-cli
uv sync
uv run pytest
uv run mod --help
```

Build the package locally:

```powershell
uv build
uvx --from ./dist/my_office_days_cli-0.1.0-py3-none-any.whl mod --help
```

## Releases

[Release Please](https://github.com/googleapis/release-please) maintains the
changelog and release pull request from Conventional Commits. Merging a release
PR creates a GitHub release. The publish workflow then builds, verifies, and
publishes the package to PyPI using Trusted Publishing.

Repository maintainers must configure a PyPI Trusted Publisher for:

- owner: `cveld`
- repository: `my-office-days-cli`
- workflow: `publish.yml`
- environment: `pypi`

## License

Licensed under the [MIT License](LICENSE).
