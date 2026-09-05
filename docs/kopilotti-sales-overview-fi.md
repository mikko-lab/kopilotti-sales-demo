# Kopilotti Sales - tuote-esittely

Kopilotti Sales digitalisoi käytetyn ajoneuvon hintaneuvottelun. Luonnollisen kielen keskustelu ja kaupallinen päätös on erotettu toisistaan: LLM voi tukea keskustelua, mutta deterministinen palvelinpuolen sääntömoottori tekee kaupallisen päätöksen jälleenmyyjän määrittämissä rajoissa.

## 1. Tuotteen tarkoitus

Ajoneuvon tiedot ja ostopolun muut vaiheet voivat olla verkossa, vaikka hintaneuvottelu vaatii edelleen manuaalista viestinvaihtoa. Kopilotti Sales muuttaa tämän vaiheen hallituksi digitaaliseksi poluksi siirtämättä kaupallista päätösvaltaa pois jälleenmyyjältä.

Jälleenmyyjä määrittää säännöt. Järjestelmä soveltaa niitä johdonmukaisesti. Automaatiorajan ulkopuoliset tapaukset eskaloidaan ihmiselle.

## 2. Asiakaspolku

1. Asiakas avaa ajoneuvokohtaisen neuvottelupolun.
2. Asiakas lähettää tarjouksen.
3. Palvelin lataa ajoneuvon ja voimassa olevan kaupallisen politiikan.
4. Sääntömoottori palauttaa tuloksen `ACCEPT`, `COUNTER`, `REJECT` tai `ESCALATE`.
5. Hyväksytty tulos voi varata ajoneuvon samassa tietokantatransaktiossa päätöksen, session tilasiirtymän ja auditointitapahtuman kanssa.
6. Asiakas jatkaa jälleenmyyjän omassa viimeistelyprosessissa, tai eskaloitu tapaus siirtyy ihmiselle.

Kopilotti Sales rajaa tehtävänsä digitaaliseen hintaneuvotteluun ja hallittuun jatkopolkuun. Jälleenmyyjä vastaa omasta kaupanteko-, maksu- ja luovutusprosessistaan.

## 3. Kaupalliset rajat

Jälleenmyyjä määrittää kaupallisen politiikan, kuten hintalattian, tavoitehinnan, listahinnan, kierrosrajat ja eskalointisäännöt. Kopilotti Sales soveltaa politiikkaa; se ei keksi hinnoittelustrategiaa.

Vanhentunut politiikka, puuttuva ajoneuvo, ajoneuvon ja politiikan ristiriita tai sääntökonflikti johtaa eskalointiin arvatun päätöksen sijaan. Ihminen säilyttää päätösvallan poikkeustilanteissa.

## 4. Deterministinen päätösmoottori

Päätösmoottori tuottaa yhden neljästä tilasta: hyväksyntä, vastatarjous, hylkäys tai eskalointi. Hintalattia rajaa hyväksynnän ja vastatarjouksen. Sama validoitu syöte ja politiikka tuottavat saman kaupallisen päätöksen.

Kaupallinen päätös tehdään LLM:stä erotetussa palvelinpuolen sääntömoottorissa. Tämä raja pienentää LLM-manipulaation vaikutusta, mutta sitä ei kuvata täydellisenä suojana kaikkia hyökkäyksiä vastaan.

## 5. Varaus ja tuplavarausten esto

PostgreSQL-malli sallii vain yhden aktiivisen varauksen samalle jälleenmyyjälle ja ajoneuvolle tietokannan pakottaman uniikki-indeksin avulla. Hyväksytty päätös, varaus, session tilasiirtymä ja auditointitapahtuma kuuluvat samaan transaktioon. Jos jokin vaihe epäonnistuu, kokonaisuus perutaan.

Varausmekanismit on toteutettu ja testattu, mutta niitä ei ole tässä yhteydessä tuotantovarmennettu.

## 6. Persistenssi ja sovelluksen auditointihistoria

Julkaistun demon tuotantobackend tallentaa neuvottelusessiot pysyvästi PostgreSQL:ään. Session käyttö on tenant-rajattu sovellusrajalla, ja tenant-suhteiden eheys pakotetaan tietokantarajoitteilla.

Ostosessioiden, idempotenssitietojen, päätösten ja auditointitapahtumien persistenssipolut sekä sovelluksen auditointihistoria ja append-only-sovelluspolku on toteutettu ja testattu, mutta ne eivät kuulu tämän rajatun tuotantovarmennuksen piiriin.

Tämä on kuvaus repon sovellus- ja tietokantakäyttäytymisestä. Se ei ole väite muuttumattomasta ulkoisesta ledgeristä, event sourcing -arkkitehtuurista tai tuotantovarmennuksesta.

## 7. DDN ja todennettavuus

DDN (Deterministic Decision Network) -valmistelu sisältää deterministisen kanonisoinnin, toisistaan erotetut hashit, rajatun lähetysadapterin sekä turvallisen kuittilinkin paikallisen muodostus- ja näyttörajan paikallisesti varmennetulle tulokselle.

Hash tukee eheyden tarkistamista, mutta hash yksin ei todista kuitin antajaa.

Live DDN -varmennus, allekirjoittajan autentikointi, quorum ja trust profile, julkinen ankkurointi sekä riippumaton offline-varmennin kuuluvat roadmapille. Nykyinen toteutus ei esitä niitä valmiina tuotanto-ominaisuuksina.

## 8. Turvallisuusrajat

- LLM voi tukea keskustelua, mutta ei päätä hintaa tai kaupallista tulosta.
- LLM-eristys pienentää manipulaation vaikutusta, mutta ei ole lupaus täydellisestä prompt injection -suojasta.
- Hash osoittaa eheyteen liittyvää johdonmukaisuutta, ei kuitin antajan identiteettiä tai luottamusketjua.
- Roadmap-ominaisuuksia ei käytetä nykyisen päätöksenteon edellytyksenä.
- Tämä esittely ei valtuuta deployta, migraatioita tai tuotantopalveluiden käyttöä.

## 9. Production-readiness-status

Tila: **rajattu tuotantovarmennus 26.8.2026**.

Julkaistun demon tuotantobackendissa varmennettiin neuvottelusessioiden pysyvä PostgreSQL-tallennus, tenant-rajattu session käyttö ja tenant-suhteiden tietokantatason eheys. Tuore backup/restore-testi sekä skeema- ja readiness-portit läpäistiin ennen julkaisua.

Tämä on rajattu tuotantovarmennus, ei koko tuotteen yleinen production-ready-väite. Varaus- ja auditointimekanismit, maksukelpoinen kauppapolku, live DDN -todennus ja VIS-tuotantoyhteys säilyvät omissa jäljempänä kuvatuissa rajoissaan.

Julkisesti kuvattu nykyinen laajuus ja tuotantorajat löytyvät [Kopilotti Salesin julkisesta README-tiedostosta](https://github.com/mikko-lab/kopilotti-sales-demo#current-scope).

## 10. Rajatusti tuotantovarmennettu 26.8.2026

<!-- sales-claim id="postgres-session-persistence" status="production-verified-scope" -->
- neuvottelusessioiden pysyvä PostgreSQL-tallennus tuotannossa
<!-- sales-claim id="tenant-scoped-negotiation-session-access" status="production-verified-scope" -->
- tenant-rajattu neuvottelusession käyttö
<!-- sales-claim id="database-enforced-tenant-relationship-integrity" status="production-verified-scope" -->
- tenant-suhteiden tietokantatason eheys
<!-- sales-claim id="readiness-schema-verification-gates" status="production-verified-scope" -->
- tuotannon skeema- ja readiness-portit
<!-- sales-claim id="verified-backup-restore" status="production-verified-scope" -->
- ennen julkaisua läpäisty backup/restore-testi

Varmennus koskee vain yllä kuvattua rajattua tuotantolaajuutta.

## 11. Toteutettu ja testattu

<!-- sales-claim id="digital-price-negotiation" status="implemented-tested" -->
- digitaalinen hintaneuvottelu
<!-- sales-claim id="llm-isolated-commercial-decision" status="implemented-tested" -->
- LLM:stä erotettu palvelinpuolen kaupallinen päätös
<!-- sales-claim id="deterministic-decision-engine" status="implemented-tested" -->
- deterministinen `ACCEPT`-, `COUNTER`-, `REJECT`- ja `ESCALATE`-logiikka
<!-- sales-claim id="dealer-commercial-boundaries-price-floor" status="implemented-tested" -->
- jälleenmyyjän määrittämät kaupalliset rajat ja hintalattian noudattaminen
<!-- sales-claim id="deterministic-canonicalization-hashes" status="implemented-tested" -->
- deterministinen kanonisointi ja hashien muodostus
<!-- sales-claim id="safe-local-receipt-link-boundary" status="implemented-tested" -->
- turvallisen kuittilinkin paikallinen muodostus- ja näyttöraja
<!-- sales-claim id="dealer-negotiation-summary-api" status="implemented-tested" -->
- autentikoitu, jälleenmyyjäkohtainen ja vain lukeva neuvotteluyhteenveto

## 12. Ei tuotantovarmennettu

<!-- sales-claim id="atomic-vehicle-reservation" status="implemented-not-production-verified" -->
- atominen ajoneuvon varaus
<!-- sales-claim id="database-enforced-double-booking-prevention" status="implemented-not-production-verified" -->
- tietokantarajoitteeseen perustuva aktiivisten tuplavarausten esto
<!-- sales-claim id="application-audit-history-hash-chain" status="implemented-not-production-verified" -->
- sovelluksen auditointihistoria ja hash-ketju
<!-- sales-claim id="append-only-audit-application-path" status="implemented-not-production-verified" -->
- auditointitapahtumien append-only-sovelluspolku
<!-- sales-claim id="dealer-summary-api-not-production-verified" status="implemented-not-production-verified" -->
- jälleenmyyjän neuvotteluyhteenveto-API

Varaus- ja auditointimekanismit on toteutettu ja testattu, mutta niitä ei ole tässä yhteydessä tuotantovarmennettu.

## 13. Roadmap ja tutkimussuunnat

<!-- sales-claim id="live-ddn-verification" status="roadmap-research" -->
- live DDN -varmennus
<!-- sales-claim id="signer-authentication-trust-profiles" status="roadmap-research" -->
- allekirjoittajan autentikointi ja kiinnitetyt trust profile -määritykset
<!-- sales-claim id="quorum-public-anchoring" status="roadmap-research" -->
- quorum-varmennus ja julkinen ankkurointi
<!-- sales-claim id="independent-offline-verifier" status="roadmap-research" -->
- riippumaton offline-varmennin
<!-- sales-claim id="byte-exact-runtime-replay" status="roadmap-research" -->
- byte-exact runtime replay
<!-- sales-claim id="signed-committed-decision-artifact" status="roadmap-research" -->
- allekirjoitettu committed decision artifact
<!-- sales-claim id="proof-gated-execution" status="roadmap-research" -->
- proof-gated execution
<!-- sales-claim id="zero-knowledge-proofs" status="roadmap-research" -->
- zero-knowledge proofs
<!-- sales-claim id="approved-rto-rpo-targets" status="roadmap-research" -->
- hyväksytyt RTO/RPO-tavoitteet
<!-- sales-claim id="named-operational-owners-response-times" status="roadmap-research" -->
- nimetyt operatiiviset omistajat ja vasteajat
<!-- sales-claim id="admin-agreed-deals-ui" status="roadmap-research" -->
- Adminin sovitut kaupat -käyttöliittymä
<!-- sales-claim id="dealer-contact-handoff-consent" status="roadmap-research" -->
- asiakkaan yhteystiedon suostumukseen perustuva jälleenmyyjä-handoff
<!-- sales-claim id="dealer-email-notification" status="roadmap-research" -->
- myyjälle lähetettävä sähköposti-ilmoitus
<!-- sales-claim id="payment-financing-features" status="roadmap-research" -->
- maksu- tai rahoitustoiminnot
<!-- sales-claim id="separate-staging-environment" status="roadmap-research" -->
- erillinen staging-ympäristö

Nämä ovat tavoite- tai tutkimussuuntia, eivät nykyisiä ominaisuuksia.

## 14. Demo ja lisätiedot

- [Avaa demo](https://app.kopilotti.online)
- [English product overview](kopilotti-sales-overview-en.md)
- [English A4 PDF](kopilotti-sales-overview-en.pdf)
- [Repon README](../README.md)
- [Lisenssi](../LICENSE)

Demo havainnollistaa tuotevirtaa. Se ei todista ei-tuotantovarmennetuiksi merkittyjen ominaisuuksien tuotantovarmennusta.
