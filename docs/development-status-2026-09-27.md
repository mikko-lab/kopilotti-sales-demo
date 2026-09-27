# Development status / Kehitystilanne — 27 September 2026

[Suomi](#suomi) · [English](#english)

## Suomi

### Mitä valmistui

Rajattu atominen ACCEPT-toteutus on yhdistetty ylläpidettyyn koodipohjaan. Se käyttää tenantin omaa ajoneuvovarastoa ja tarkistaa ajoneuvon, version, hinnan sekä neuvottelusession käyttöoikeuden.

Hyväksyntä tallentaa sovitun hinnan, kauppatietueen, neuvottelusidonnan, varauksen, varastolukon, auditoinnin ja jatkokäsittelyn tapahtumat samassa tietokantatransaktiossa. Jos jokin kirjoitus epäonnistuu, kaikki tämän hyväksynnän kirjoitukset perutaan. Tietokannan eheysrajat estävät sidonnan väärään tenanttiin, ajoneuvoon tai sessioon. Uusintapyyntö palauttaa tallennetun päätöksen luomatta uutta kauppaa; se ei uusi vanhentunutta varausta.

Peruutus ja vanheneminen vapauttavat hyväksynnän varauksen ja lukon atomisesti. Tämä rajattu palvelu ei pura maksuvaiheeseen edenneitä kauppoja. Sähköpostivarmennusta ei rinnasteta vahvaan tunnistautumiseen eikä teknistä ACCEPT-päätöstä oikeudellisesti sitovaan sopimukseen.

### Varmennus ja sen rajat

Alla ovat ylläpitäjän raportoimat, 27.9.2026 yhdistetylle toteutukselle toteutuneet CI-tulokset. Ne koskevat yksityistä sovellustoteutusta, eivät tämän julkisen esittelyrepon testisarjaa tai tuotantoympäristön auditointia. Testikoodi ja raakalokit eivät kuulu tähän julkiseen repoon.

| Tarkistus | Tulos |
|---|---|
| Päätestisarja | 1059 testiä: 1058 läpi, 0 epäonnistunutta, 1 ohitus |
| Persistence, PostgreSQL 15 ja 18 | 136/136 kummassakin |
| Core ja atominen transaktioraja, PostgreSQL 15 ja 18 | 23/23 kummassakin; PG15-tapaukset sisältyvät myös pääsarjaan |
| Playwright-selaintestit | 31/31 |

Yksi ohitettu testi vaatii erillisen Kafka/Debezium-ympäristön; sitä ei lasketa hyväksytyksi. Testit kattavat muun muassa kirjoitusvirheiden rollbackin, samanaikaiset hyväksynnät, uusinnat, tenant-/ajoneuvosidonnat sekä peruutuksen ja vanhenemisen. CI-tulos ei yksin osoita tuotantovalmiutta.

### Mitä tämä ei ota käyttöön

Uusi polku ei ole kytketty nykyisiin HTTP-, demo-, jälleenmyyjä- tai ostopolkuihin. Pelkkä version julkaiseminen ei aktivoi sitä, eikä sitä kytketä päälle ympäristömuuttujalla. Maksut, ajoneuvon luovutus ja vastatarjouksen hyväksyminen tarvitsevat erillisen integraation. Julkinen demo säilyy ei-sitovana, eikä Kopilotti vastaanota, säilytä tai välitä asiakkaan varoja.

Käyttöönotto edellyttää tuotannon tietokantarakenteen ja olemassa olevien sidontojen tarkistamista, migraatioiden ja sovellusversion yhteensovittamista, palautussuunnitelmaa sekä erikseen hyväksyttyä rajattua kytkentää. Virheellistä vanhaa sidontaa ei korjata arvaamalla tai poisteta vain migraation läpäisemiseksi. Tämän päivityksen yhteydessä uutta core-polun toimintaa ei julkaistu tuotantokäyttöön.

## English

### What has been completed

A bounded atomic ACCEPT implementation has been merged into the maintained codebase. It uses the tenant's own vehicle inventory and validates the vehicle, revision, price and access to the negotiation session.

Acceptance persists the agreed price, deal record, negotiation binding, reservation, inventory lock, audit and downstream events in one database transaction. If any write fails, all writes for that acceptance roll back. Database integrity constraints reject bindings to the wrong tenant, vehicle or session. A retry returns the stored decision without creating another deal; it does not renew an expired reservation.

Cancellation and expiry release the acceptance reservation and lock atomically. This bounded service does not cancel deals that have progressed to payment. Email verification is not treated as strong identity verification, and a technical ACCEPT decision is not presented as a legally binding contract.

### Verification and its limits

These are maintainer-reported CI results for the implementation merged on 27 September 2026. They concern the private application implementation, not this public showcase repository's test suite or a production-environment audit. The test code and raw logs are not included in this public repository.

| Check | Result |
|---|---|
| Main test suite | 1059 tests: 1058 passed, 0 failed, 1 skipped |
| Persistence, PostgreSQL 15 and 18 | 136/136 on each version |
| Core and atomic transaction boundary, PostgreSQL 15 and 18 | 23/23 on each version; PG15 cases are also included in the main suite |
| Playwright browser tests | 31/31 |

The skipped test needs a separate Kafka/Debezium environment and is not counted as passed. Coverage includes rollback on write failures, concurrent acceptances, retries, tenant/vehicle bindings, cancellation and expiry. CI success alone does not establish production readiness.

### What this does not enable

The new path is not connected to existing HTTP, demo, dealer or purchase flows. Deploying a release alone does not activate it, and no environment variable enables it. Payments, vehicle handover and acceptance of a counter-offer require separate integration. The public demo remains non-binding, and Kopilotti does not receive, hold or transfer customer funds.

Rollout requires inspection of the production schema and existing bindings, coordinated database migrations and application versions, a rollback plan and a separately approved bounded integration. Invalid existing bindings must not be guessed or deleted merely to make a migration pass. This update did not release the new core path into production use.
