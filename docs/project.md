# Project en status

## Doel

Een CLI waarmee de gebruiker zijn eigen My Office Days-account kan bedienen,
uiteindelijk minimaal:

- eigen boekingen bekijken;
- beschikbare locaties, dagen en voorzieningen bekijken;
- een kantoor-/werkplekreservering maken;
- een eigen reservering annuleren;
- machineleesbare JSON-uitvoer leveren voor een agent-skill.

## Huidige status

De CLI ondersteunt veilige lokale configuratie, login per e-mailcode,
versleuteld GraphQL-transport, gebouwen, boekingstypes, beschikbaarheid en eigen
boekingen. Boeking maken is live gevalideerd en gebruikt planweergave,
expliciete bevestiging en read-back-verificatie. Annuleren blijft uitgeschakeld
totdat de volledige semantiek veilig is gevalideerd.

## Architectuur

- `src/my_office_days/cli.py`: CLI-opdrachten en presentatie.
- `src/my_office_days/config.py`: niet-geheime configuratie onder LocalAppData.
- `src/my_office_days/auth.py`: employee session en encryptiesleutel in Windows
  Credential Manager via Python keyring.
- `src/my_office_days/client.py`: kleine HTTP-client met consistente fouten.
- `.github/workflows/`: CI, Release Please en publicatie naar PyPI.

## Ontwerpkeuzes

Gebruik eerst de mobiele API in plaats van UI-automatisering: die is sneller en
minder gevoelig voor lay-outwijzigingen. Gebruik alleen het eigen account en
respecteer autorisatie, privacy en serverlimieten. UI-automatisering via ADB is
een tijdelijke onderzoeksmethode, geen gewenste productie-interface.
