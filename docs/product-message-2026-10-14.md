# Kopilotti Sales — tuoteviesti / product message

## Suomi

Kopilotti Sales on digitaalinen automyyjä ja autoliikkeen myyntikanava. Se käy hintaneuvottelun ja hyväksyy hinnan autoliikkeen valtuuttamana, liikkeen määrittämissä rajoissa.

Sovittu kauppa tarkoittaa tässä, että kohdeauto ja hinta on sovittu liikkeen valtuuttamana. Myyjän ei tarvitse aloittaa samaa hintaneuvottelua uudelleen. Sopimus, sähköinen allekirjoitus sekä maksu tai rahoitus ovat vielä erillisiä vaiheita; auto ei ole tämän perusteella maksettu tai luovutettu. Hinnan ja saatavuuden voimassaolo tarkistetaan sovittujen ehtojen mukaan.

Julkinen demo on ei-sitova esittely. Listahinta- ja neuvottelupolut on toteutettu, mutta nykyinen polku pysähtyy ennen oikeaa maksua tai rahoitusta. Uusi atominen kauppatietue-, varaus- ja varastolukkopolku on toteutettu ja testattu erikseen, eikä sitä ole kytketty nykyisiin asiakaspolkuihin. Käyttöönotto edellyttää saatavuuden, tietojen siirron sekä sopimus-, allekirjoitus- ja maksu- tai rahoitusyhteyksien varmennusta.

## English

Kopilotti Sales is a digital car salesperson and a sales channel for dealerships. It negotiates and accepts a price on the dealer’s behalf, within the authority and limits set by the dealer.

An agreed deal means that the vehicle and price have been agreed under the dealer’s authority. The salesperson does not need to restart the same price negotiation. The contract, electronic signature and payment or financing remain separate steps; the vehicle is not yet paid for or handed over. Price validity and availability are checked under the agreed terms.

The public demo is a non-binding demonstration. List-price and negotiated-price paths are implemented, but the current flow stops before real payment or financing. The new atomic deal-record, reservation and inventory-lock path is implemented and tested separately and is not connected to the current customer journeys. Rollout requires verified availability, data handoff, contract, electronic-signature and payment or financing connections.

## Vastuut / Responsibilities

Liike määrittää kaupallisen toimivallan. Palvelimen deterministinen sääntömoottori tekee hintapäätökset; kielimalli ei päätä hintaa. Poikkeukset siirtyvät ihmiselle. Liike ja sen valitsemat palveluntarjoajat hoitavat sopimuksen, sähköisen allekirjoituksen sekä maksun tai rahoituksen. Rahat maksetaan suoraan myyjäliikkeelle.

The dealer defines commercial authority. A deterministic server-side policy engine makes price decisions; the language model does not set prices. People handle exceptions. The dealership and its selected providers handle the contract, electronic signature and payment or financing. Funds go directly to the selling dealership.

## Tietojen siirto / Data handoff

Liikkeelle rajattu yhteenvetorajapinta näyttää sovitun hinnan, ajoneuvon ja tarjousten rakenteellisen historian tai ihmiselle arvioitavan tilanteen. Se ei välitä ostajan yhteystietoja. Automaattinen DMS-/CRM-siirto ja suostumukseen perustuva yhteystietojen välitys vaativat jatkototeutuksen.

The dealer-scoped summary API exposes the agreed price, vehicle and structured offer history, or a case for human review. It does not transfer buyer contact details. Automatic DMS/CRM handoff and consent-based contact transfer require further implementation.

## Ymmärrettävyystesti / Reader comprehension test

Näytä sivu ensin 10 sekunniksi autoliikkeen päättäjälle, auton ostajalle ja markkinapaikka- tai DMS-kumppanille. Kysy ilman johdattelua: Mitä Sales tekee? Mitä se saa päättää? Mitä tapahtuu hinnan hyväksymisen jälkeen? Anna sitten lukea koko sivu ja kysy: Kuka hoitaa sopimuksen, allekirjoituksen ja maksun? Milloin ihminen tulee mukaan? Mitä demo todistaa ja mitä pitää vielä yhdistää? Kirjaa sanatarkat vastaukset ja kohdat, joihin tulkinta perustuu.

Show the page for ten seconds to a dealer decision-maker, buyer and marketplace or DMS partner. Ask without prompting: What does Sales do? What can it decide? What happens after price acceptance? Then let them read the full page and ask who handles the contract, signature and payment, when a person gets involved, and what the demo proves versus what still needs integration. Record exact answers and the page elements behind each interpretation.

Hyväksymiskriteeri: vastaus erottaa valtuutetun hinnan sopimisen kiinnostuksen ilmaisusta, allekirjoituksesta ja maksusta sekä tunnistaa integraatiorajat. Testiä ei ole toteutettu oikeilla lukijoilla. Yhteydenottoja ei ole lähetetty.

Acceptance criterion: the answer distinguishes authorised price agreement from expressed interest, signature and payment, and recognises integration boundaries. This test has not been run with real readers. No outreach has been sent.
