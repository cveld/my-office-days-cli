# Authenticatie en veiligheid

## Lokale gegevens

- Niet-geheime configuratie:
  `%LOCALAPPDATA%\my-office-days-cli\config.json`
- Employee session en eventuele encryptiesleutel: aparte entries in de
  OS-keyring onder service `my-office-days-cli`.
- APK, captures en onderzoeksartefacten:
  externe OneDrive-projectmap of expliciet genegeerde paden.

De CLI accepteert voor tijdelijke automatisering ook `MOD_TOKEN`, maar een
environment variable kan zichtbaar zijn voor lokale processen en logs. De
keyring heeft daarom de voorkeur.

`mod auth login` toont of bewaart het e-mailadres en de eenmalige code niet. De
employee GUID is niet geheim en wordt in `config.json` opgeslagen; de ontvangen
`authorisation` en optionele `key` gaan uitsluitend naar de OS-keyring.

## Mutaties

Voor iedere reservering of annulering:

1. lees eerst de actuele toestand;
2. toon datum, locatie, voorziening en eventuele boekings-ID;
3. vraag expliciete bevestiging;
4. voer precies één mutatie uit;
5. lees terug en verifieer het resultaat.

Log nooit volledige requestheaders. Redigeer `Authorization`, cookies, e-mail,
naam, personeelsnummer en andere persoonsgegevens.
