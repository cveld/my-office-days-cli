# Bevestigd API-contract

Onderstaand contract is afgeleid uit de officiële Android-app. De read-only
calls en het maken van een boeking zijn live gevalideerd met een eigen account.

## Basis-URL en tenantselectie

- Productie v1: `https://server.werktopkantoor.nl/`, waarna de app de
  tenantprefix en customer-id toevoegt.
- Productie v2: `https://{{customer}}.server.werktopkantoor.nl/<customer>`,
  waarbij underscores en koppeltekens alleen uit de hostnaam worden verwijderd.
  De customer-id blijft als padsegment staan. Voorbeeldstructuur:
  `https://tenant.server.werktopkantoor.nl/tenant`.
- GraphQL-pad: `connection/graphql`.
- De CLI verwacht voorlopig de volledig samengestelde tenant-basis-URL,
  inclusief het customer-pad. Deze wordt lokaal ingesteld en niet in de skill
  hardcoded.

Bron/bewijs: Hermes-bundle, modules rond `ConfigClient`, `apiConfigProduction`
en `GraphqlBuilder`.

## Authenticatie

- De waarde uit app-opslagveld `employee_session` wordt letterlijk als
  `Authorization`-header verzonden; er wordt geen `Bearer `-prefix toegevoegd.
- De app kent een JWT-modus waarin request- en response-inhoud aanvullend met
  AES-CBC en dubbele Base64-codering wordt verwerkt. De CLI ondersteunt deze
  variant voor GraphQL-calls en bewaart de ontvangen sleutel veilig.
- Login-link aanvragen: `POST /connection/rest/employee/reset` met velden
  `email`, `forceEmail` en `accessTo` (standaard `app`), zonder authenticatie.
- Login-token verifiëren: `POST /connection/rest/employee/authenticate` met
  `email` en `token`, zonder authenticatie.
- Beide loginrequests gebruiken `application/x-www-form-urlencoded`. Een
  succesvolle resetrespons heeft `status: success` en kan `sent_to` bevatten.
  Een succesvolle authenticate-respons heeft `status: success` en bevat
  minimaal `guid` en `authorisation`; `key` is optioneel en activeert de
  aanvullende JWT-codering.

Bron/bewijs: Hermes-bundle, `sendToken`, `verifyToken` en `createAxiosClient`.

## GraphQL-transport

Method + path: `POST connection/graphql`

Requestbody is een JSON-array. Elk item bevat:

```json
[{"name":"operation-name","query":"...","variables":{}}]
```

De niet-JWT-route verstuurt deze array rechtstreeks. Bij succes leest de app
per item `data`; GraphQL-fouten staan per item onder `errors`.

Bron/bewijs: Hermes-disassembly van `GraphqlBuilder.addQuery`,
`GraphqlBuilder.execute` en de response-parser.

## Gebouwen bekijken

Method + path: `POST connection/graphql`

GraphQL-operatie: `query buildings`; bevestigde velden zijn onder meer `guid`,
`name`, `capacity`, `position`, `available_for`, `kind`, `active` en het
adresobject.

Bron/bewijs: Hermes-bundle, querymodule `buildings`.

## Eigen boekingen bekijken

Method + path: `POST connection/graphql`

GraphQL-operatie: `query employee($guid: String!, $booking_date: [String],
$active: [String])`. De app gebruikt:

- `guid`: de eigen employee GUID;
- `booking_date`: filters zoals `YYYY-MM-DD`, `YYYY-MM-DD_after_equal` en
  `YYYY-MM-DD_before_equal`;
- `active`: `["yes"]` voor actieve boekingen.

Bevestigde boekingsvelden zijn onder meer `guid`, `booking_date`, `kind`,
`transport_kind`, `reason`, `status`, `active`, gebouw, verdieping, ruimte,
tafel en tijdslot.

Bron/bewijs: Hermes-bundle, booking fetch-module en booking-fragmenten.

## Beschikbaarheid bekijken

GraphQL-operatie: `query booking_capacity($dates: [String], $kinds: [String],
$subKinds: [String], $employeeGuid: String)`. De read-only respons bevat per
item onder meer datum, item- en timeslotsoort, gebouw/verdieping/ruimte,
`capacity`, `remaining`, blokkadecommentaar en exceptionsoort.

Bron/bewijs: Hermes-bundle, `fetchAllRange` en querymodule
`booking_capacity`.

## Boeking maken en annuleren

De app bevat een `create_employee_booking`-mutatie met bevestigde inputvelden en
een `booking_cancel`-mutatie met `guid` en `active`. Maken is beschikbaar met
planweergave, expliciete bevestiging en read-back-verificatie. Annuleren blijft
uitgeschakeld totdat de volledige annuleringssemantiek veilig is gevalideerd.

Laatst bevestigd: 2026-10-09, Android app build 3.12.10.

Neem geen tokens, cookies, echte namen, e-mailadressen, reserverings-ID's of
andere persoonsgegevens op.
