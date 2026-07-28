# Kopilotti Sales

Kopilotti Sales on kaupallinen ohjelmistotuote.

Tämä repositorio esittelee tuotteen toimintaa ja arkkitehtuuria.

Julkinen repositorio ei sisällä tuotannon päätösmoottoria eikä jälleenmyyjäkohtaisia sääntöjä.

![Status](https://img.shields.io/badge/status-active%20development-orange)
![Platform](https://img.shields.io/badge/platform-web-blue)
![License](https://img.shields.io/badge/license-proprietary-lightgrey)

→ [Avaa Kopilotti Sales -demo](https://kopilotti-sales-demo.vercel.app/)

> **Perinteinen verkkokauppa digitalisoi listahintaisen ostamisen.**
>
> **Kopilotti Sales digitalisoi hintaneuvottelun.**

Kopilotti Sales on digitaalinen myyntikanava käytettyjen ajoneuvojen hintaneuvotteluun.

Se mahdollistaa turvallisen digitaalisen hintaneuvottelun, joka kasvattaa kauppojen määrää säilyttäen myyjäliikkeen päätösvallan. Kaikki kaupalliset päätökset tehdään deterministisesti myyjäliikkeen omien liiketoimintasääntöjen mukaisesti.

Kopilotti Sales ei ole chatbot.

Kopilotti Sales ei ole automaattinen hinnoittelujärjestelmä.

Kopilotti Sales ei korvaa automyyjää.

Se digitalisoi käytettyjen ajoneuvojen kaupan viimeisen merkittävän manuaalisen vaiheen ennen kauppoja.

---

# Keskeinen ajatus

> **LLM voi keskustella asiakkaan kanssa.**
>
> **LLM voi analysoida ja ehdottaa.**
>
> **LLM ei koskaan päätä hintaa.**

Kaikki kaupalliset päätökset tehdään deterministisesti myyjäliikkeen liiketoimintasääntöjen perusteella.

Tämä erottaa Kopilotti Salesin tavallisista AI-chatboteista ja automatisoiduista hinnoittelujärjestelmistä.

---

# Mikä ongelma ratkaistaan?

Käytettyjen ajoneuvojen verkkokaupassa lähes koko ostoprosessi voidaan jo hoitaa digitaalisesti.

Asiakas voi:

- löytää ajoneuvon verkosta
- vertailla vaihtoehtoja
- hakea rahoituksen
- tutustua myynti-ilmoitukseen ja kuntoraporttiin
- tehdä kaupat
- siirtyä maksuprosessiin

Yksi vaihe on kuitenkin usein edelleen manuaalinen.

Hintaneuvottelu.

Monessa autoliikkeessä asiakkaan tarjous johtaa edelleen samaan ketjuun:

```text
Asiakas
   │
   ▼
Myyjä
   │
   ▼
Vaihtoautopäällikkö
   │
   ▼
Päätös
   │
   ▼
Asiakas odottaa vastausta
```

Juuri tässä vaiheessa ostohalukkuus voi kadota.

Kopilotti Sales poistaa odotuksen silloin, kun päätös voidaan tehdä turvallisesti myyjäliikkeen liiketoimintasääntöjen mukaisesti.

Kun tapaus vaatii ihmisen harkintaa, se siirtyy myyjäliikkeen käsiteltäväksi.

---

# Hintaneuvottelu on osa ostokäyttäytymistä

Käytetyn ajoneuvon ostaminen kuuluu useimmille kotitalouksille suurimpiin yksittäisiin hankintoihin oman kodin jälkeen.

Tässä tuoteryhmässä hinnasta neuvotteleminen on vuosikymmeniä ollut luonnollinen osa ostokäyttäytymistä.

Monelle asiakkaalle listahinta ei ole keskustelun päätös.

Se on keskustelun lähtökohta.

Perinteinen verkkokauppa perustuu kiinteään listahintaan.

Kopilotti Sales ei pyri muuttamaan asiakkaiden ostokäyttäytymistä.

Se digitalisoi sen.

Asiakas voi hyväksyä listahinnan tai aloittaa hintaneuvottelun saman digitaalisen kaupankäyntiprosessin aikana.

---

# Mitä Kopilotti Sales tekee?

Kopilotti Sales toimii digitaalisena automyyjänä, joka voi:

- käydä hintaneuvottelun asiakkaan kanssa
- tehdä vastatarjouksia myyjäliikkeen hinnoittelusääntöjen mukaisesti
- hyväksyä tarjouksen liiketoimintasääntöjen sallimissa rajoissa
- eskaloida poikkeustapaukset ihmiselle
- muodostaa kauppa sovitulla hinnalla
- käynnistää maksuprosessi

Kopilotti Salesin tehtävä päättyy sovitulla hinnalla muodostettuun kauppaan ja maksuprosessin käynnistämiseen.

Tämän jälkeen myyjäliike sopii asiakkaan kanssa ajoneuvon luovutuksesta normaalin toimintatapansa mukaisesti.

---

# Mitä Kopilotti Sales ei tee?

Kopilotti Sales:

- ei valitse asiakkaalle ajoneuvoa
- ei arvioi ajoneuvon kuntoa
- ei keskustele kuntoraportin sisällöstä
- ei tulkitse huoltohistoriaa
- ei määritä hinnoittelustrategiaa
- ei hallitse ajoneuvoja
- ei korvaa automyyjää
- ei sovi ajoneuvon luovutuksesta
- ei tee kaupallisia päätöksiä LLM:n perusteella

Sen tehtävä on yksi:

viedä asiakas turvallisesti hintaneuvottelusta toteutuneisiin kauppoihin.

---

# Missä vaiheessa Kopilotti Sales tulee mukaan?

Kopilotti Sales ei ole asiakkaan ensimmäinen kosketuspiste.

Ennen hintaneuvottelun aloittamista asiakkaalla tulee olla käytettävissään kaikki ostopäätöksen kannalta olennaiset tiedot.

Näihin kuuluvat:

- myynti-ilmoitus
- myyjäliikkeen laatima kuntoraportti

Kun asiakas on tutustunut ajoneuvoon ja päättänyt edetä kohti kauppoja, Kopilotti Sales ottaa vastuun ostoprosessin viimeisestä vaiheesta.

Kopilotti Sales on rakennettu yhtä tarkoitusta varten:

turvalliseen digitaaliseen hintaneuvotteluun ennen kauppoja.

---

# Miksi kuntoraportti on pakollinen?

Kopilotti Sales keskustelee vain hinnasta.

Ajoneuvon kunto, varusteet, huoltohistoria ja muut ostopäätökseen vaikuttavat tiedot kuuluvat myynti-ilmoitukseen ja myyjäliikkeen laatimaan kuntoraporttiin.

Ajoneuvo voidaan julkaista Kopilotti Sales -myyntikanavaan vain, jos kuntoraportti on asiakkaan saatavilla ennen hintaneuvottelun aloittamista.

Kopilotti Sales ei arvioi ajoneuvon kuntoa eikä ota kantaa kuntoraportin sisältöön.

Se edellyttää, että myyjäliike on dokumentoinut ajoneuvon kunnon luotettavasti ennen digitaalisen hintaneuvottelun aloittamista.

Tämä suojaa sekä asiakasta että myyjäliikettä.

---

# Yksi digitaalinen kaupankäyntiprosessi

Asiakas voi:

- hyväksyä listahinnan ja tehdä kaupat
- aloittaa hintaneuvottelun myyjäliikkeen liiketoimintasääntöjen mukaisesti

Molemmat vaihtoehdot käyttävät samaa kaupankäyntimoottoria.

Näin ostokokemus pysyy yhtenäisenä riippumatta siitä, hyväksyykö asiakas listahinnan vai haluaako hän neuvotella hinnasta.

Kun päätös voidaan tehdä automaattisesti, asiakas saa vastauksen välittömästi.

Kun tapaus vaatii ihmisen harkintaa, se siirtyy myyjäliikkeen käsiteltäväksi.

Myyjäliikkeen päätösvalta säilyy kaikissa tilanteissa.

---

# Arkkitehtuuri

```text
                     Asiakas
                        │
                        ▼
                Kopilotti Sales
                        │
                        ▼
              Negotiation Engine
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
  Deterministiset                LLM-analyysi
 liiketoimintasäännöt           ja keskustelu
          │                           │
          └─────────────┬─────────────┘
                        ▼
        ACCEPT · COUNTER · REJECT · ESCALATE
                        │
                        ▼
               Kauppa ja maksuprosessi
```

LLM voi osallistua keskusteluun, tunnistaa asiakkaan tarkoituksen ja muodostaa luonnollisen vastauksen.

Deterministinen päätöksentekokerros tekee kaikki kaupalliset päätökset.

Päätöksenteko ei perustu mallin mielipiteeseen, todennäköisyyteen tai vapaamuotoiseen tekstivastaukseen.

---

# Arkkitehtuuriperiaatteet

Kopilotti Sales perustuu yksinkertaiseen periaatteeseen:

LLM keskustelee. Backend päättää.

Kaikki kaupalliset päätökset tehdään deterministisesti myyjäliikkeen liiketoimintasääntöjen mukaisesti.

Tämän vuoksi järjestelmä on:

- auditoitava
- ennustettava
- testattava
- selitettävä
- riippumaton yksittäisen kielimallin päätöksenteosta

Kaupalliset päätökset on eristetty LLM:ään kohdistuvista prompt injection -yrityksistä.

---

# Tietoturva ja arkkitehtuuri

LLM käy keskustelun asiakkaan kanssa.

LLM ei päätä hintaa.

Hintapäätöksiä ei koskaan tehdä kielimallin perusteella.

Kaikki kaupalliset päätökset tehdään deterministisessä backendissä, joka tarkistaa aina myyjäliikkeen omat säännöt ennen hyväksyntää.

Tämä arkkitehtuuri on tietoinen suunnitteluratkaisu.

Tarkkaa päätöslogiikkaa ei julkaista tässä repositoriossa.

---

# Olemassa olevat myyntikanavat, uusi toimintamalli

Useimmilla autoliikkeillä asiakkaat ottavat jo yhteyttä esimerkiksi:

- verkkopalvelun kautta
- chatissa
- WhatsAppilla
- sähköpostitse
- puhelimitse

Kopilotti Sales ei korvaa näitä kanavia eikä rakenna autoliikkeelle uutta verkkokauppaa.

Se digitalisoi hintaneuvottelun osaksi nykyistä myyntiprosessia.

Kun päätös voidaan tehdä liiketoimintasääntöjen perusteella, asiakas saa vastauksen sekunneissa.

Kun tilanne vaatii ihmisen harkintaa, asia siirtyy myyjäliikkeen käsiteltäväksi.

---

# Mitä autoliike ostaa?

Autoliike hankkii digitaalisen myyntikanavan käytettyjen ajoneuvojen hintaneuvotteluun — ei uutta verkkokauppaa, chatbottia tai automaattista hinnoittelijaa.

Tavoitteena on kasvattaa kauppojen määrää vaarantamatta myyjäliikkeen katetta tai päätösvaltaa.

---

# Kopilotti Platform

Kopilotti Sales — tämän repositorion tuote — on osa laajempaa Kopilotti-tuoteperhettä.

Jokaisella tuotteella on oma selkeä vastuunsa, ja yhdessä ne muodostavat saman myyntiprosessin toisiaan täydentävät osat.

```text
Kopilotti Platform

├── Kopilotti
│   AI Sales Copilot myyjälle
│
├── Kopilotti Sales
│   Digitaalinen automyyjä asiakkaalle
│
├── Kopilotti Admin
│   Ajoneuvot, DMS-integraatiot ja liiketoimintasäännöt
│
└── Kopilotti Insights
    Myynti-, neuvottelu- ja käyttäytymisanalytiikka
```

- **Kopilotti** tukee ihmismyyjää asiakaskeskustelun aikana. Se tunnistaa ostosignaaleja, ehdottaa seuraavia toimenpiteitä, tuottaa CRM-yhteenvedon ja suosittelee asiakkaalle sopivia autoja.
- **Kopilotti Sales** palvelee asiakasta suoraan ja vie digitaalista autokauppaa eteenpäin 24/7 determinististen liiketoimintasääntöjen rajoissa.
- **Kopilotti Admin** hallitsee ajoneuvodataa, DMS-tuonteja, jälleenmyyjäkohtaisia asetuksia ja neuvottelupolitiikkoja.
- **Kopilotti Insights** kokoaa järjestelmän tuottaman myynti-, neuvottelu- ja käyttäytymisdatan raportointia varten.

Kopilotti ja Kopilotti Sales eivät ole kilpailevia tuotteita, vaan saman myyntiprosessin toisiaan täydentäviä osia: Kopilotti auttaa ihmismyyjää, ja Kopilotti Sales palvelee asiakasta itsenäisesti silloin, kun myyjää ei ole saatavilla tai asiakas haluaa edetä digitaalisesti.

Yhdessä tuotteet muodostavat AI-avusteisen kaupankäyntialustan, joka kattaa käytettyjen ajoneuvojen myyntiprosessin ensimmäisestä asiakaskontaktista toteutuneeseen kauppaan, hallintaan ja analytiikkaan.

## Kopilotti

Kopilotti on AI Sales Copilot ihmismyyjälle — se tukee myyjää asiakaskeskustelun aikana, ei korvaa häntä eikä tee kaupallisia päätöksiä.

Sen tehtäviin kuuluvat:

- ostosignaalien tunnistaminen asiakaskeskustelusta
- seuraavien toimenpiteiden ehdottaminen myyjälle
- CRM-yhteenvedon tuottaminen
- sopivien ajoneuvojen suositteleminen asiakkaalle

Kopilotti palvelee myyjää; Kopilotti Sales palvelee asiakasta suoraan silloin, kun myyjää ei ole saatavilla tai asiakas haluaa edetä digitaalisesti.

## Kopilotti Sales

Kopilotti Sales on asiakkaalle näkyvä digitaalinen myyntikanava.

Sen vastuulla ovat:

- digitaalinen hintaneuvottelu
- liiketoimintasääntöjen mukainen päätöksenteko
- kaupan muodostaminen
- maksuprosessin käynnistäminen

Sales ei hallitse ajoneuvoja, määritä hinnoittelua tai sisällä liiketoimintasääntöjen ylläpitoa.

## Kopilotti Admin

Kopilotti Admin on myyjäliikkeen hallintajärjestelmä.

Sen avulla hallitaan:

- ajoneuvot
- DMS-tuonnit
- julkaistavat ajoneuvot
- kuntoraportit
- liiketoimintasäännöt
- käyttäjät
- toimipisteet

Kaikki Salesin tekemät kaupalliset päätökset perustuvat Adminissa ylläpidettyihin liiketoimintasääntöihin.

Sales ei sisällä kovakoodattuja hintarajoja tai jälleenmyyjäkohtaisia päätöksiä.

## Kopilotti Insights

Kopilotti Insights tuo näkyväksi digitaalisen myyntikanavan suorituskyvyn.

Esimerkkejä analytiikasta:

- hintaneuvottelujen määrä
- hyväksyttyjen tarjousten määrä
- vastatarjousten määrä
- eskaloitujen tapausten määrä
- toteutuneet kaupat
- konversio
- vastausajat
- ostokäyttäytymisen analytiikka
- myyntikanavien vertailu

Insights auttaa kehittämään myyntiprosessia tiedolla eikä oletuksilla.

---

# Tuotefilosofia

Kopilotti Sales rakentuu neljän periaatteen ympärille.

## Myyjäliike päättää

Kaikki kaupalliset päätökset perustuvat myyjäliikkeen määrittämiin liiketoimintasääntöihin.

## Asiakas tietää, mitä on ostamassa

Hintaneuvottelu alkaa vasta sen jälkeen, kun asiakkaalla on käytettävissään myynti-ilmoitus ja kuntoraportti.

## Digitaalinen kaupankäynti ei saa pysähtyä kellonaikaan

Asiakkaan ei tarvitse odottaa seuraavaan työpäivään saadakseen vastauksen silloin, kun päätös voidaan tehdä turvallisesti automaattisesti.

## Ihminen ratkaisee poikkeukset

Kun tilanne vaatii harkintaa, päätös siirtyy myyjäliikkeelle.

Kopilotti Sales ei korvaa ihmistä.

Se vapauttaa ihmiset niihin tilanteisiin, joissa heidän asiantuntemuksensa tuottaa eniten arvoa.

---

# Kenelle Kopilotti Sales on tarkoitettu?

Kopilotti Sales on suunniteltu erityisesti autoliikkeille, jotka:

- myyvät käytettyjä ajoneuvoja
- käyttävät digitaalista myyntiä
- vastaanottavat hintatarjouksia digitaalisissa kanavissa
- haluavat kasvattaa kauppojen määrää
- haluavat nopeuttaa asiakkaan päätöksentekoa
- haluavat säilyttää päätösvallan kaupallisissa ratkaisuissa

---

# Roadmap

## Kopilotti Admin

Suunnitteilla:

- DMS-integraatiot
- ajoneuvojen hallinta
- kuntoraporttien hallinta
- liiketoimintasääntöjen hallinta
- käyttäjähallinta
- toimipisteiden hallinta
- julkaisu- ja hyväksyntäprosessit

## Kopilotti Insights

Suunnitteilla:

- ostokäyttäytymisen analytiikka
- digitaalisen hintaneuvottelun analytiikka
- kauppojen analytiikka
- konversioraportit
- vastausaikojen seuranta
- liiketoimintaraportointi

## Vaihtoauton lisääminen

Vaihtoauton lisääminen digitaaliseen kaupankäyntiprosessiin kuuluu tuotteen roadmapiin.

Tavoitteena on mahdollistaa asiakkaan vaihtoauton tietojen lisääminen osaksi digitaalista kaupankäyntiä.

Vaihtoauton lopullinen arviointi ja hyvityshinta säilyvät kuitenkin aina myyjäliikkeen vastuulla.

## Monikanavainen asiointi

Tulevaisuudessa sama neuvotteluprosessi voidaan liittää useisiin digitaalisiin kanaviin, kuten verkkopalveluun, chattiin ja WhatsAppiin.

Kanava voi vaihtua.

Liiketoimintasäännöt ja päätöksenteko pysyvät samoina.

---

# Teknologia

Kopilotti Sales hyödyntää moderneja ohjelmistokomponentteja digitaalisen kaupankäyntiprosessin toteuttamiseen.

Keskeisiä teknisiä periaatteita ovat:

- selainpohjainen saavutettava käyttöliittymä
- backendissä toimiva päätöksentekomoottori
- deterministiset liiketoimintasäännöt
- tilallinen neuvotteluprosessi
- LLM eristettynä epäluotettavaksi analyysi- ja keskustelukerrokseksi
- kaupallisten päätösten audit trail
- testattavat hyväksyntä-, vastatarjous-, hylkäys- ja eskalointipolut

Teknologia ei kuitenkaan ole tuotteen ydin.

Tuotteen ydin on turvallinen digitaalinen hintaneuvottelu, joka noudattaa myyjäliikkeen liiketoimintasääntöjä.

Teknologia tukee tätä tavoitetta.

Ei päinvastoin.

---

# Kuvakaappaukset

![Kopilotti Sales -etusivu](assets/screenshot-landing.jpg)

![Ajoneuvosivu ja digitaalinen hintaneuvottelu](assets/screenshot-negotiation-card.jpg)

---

# Demo

Tämä repositorio sisältää demonstraation Kopilotti Salesin toiminnasta.

Julkiseen versioon eivät kuulu tuotantoympäristön integraatiot, jälleenmyyjäkohtaiset asetukset, hinnoittelupolitiikat eivätkä kaupalliset integraatiot.

---

# Projektin tila

Status: Active Development

Tuote kehittyy vaiheittain.

Ensimmäinen vaihe keskittyy digitaaliseen hintaneuvotteluun, kaupantekoon ja maksuprosessin käynnistämiseen.

Seuraavat vaiheet laajentavat kokonaisuutta hallintaan, analytiikkaan, integraatioihin ja monikanavaiseen asiointiin.

---

# Lisenssi

Kopilotti Sales on omisteinen ohjelmisto. Lähdekoodin kopiointi, muokkaaminen, levittäminen tai kaupallinen käyttö ilman tekijän etukäteen antamaa kirjallista lupaa on kielletty.

Katso tarkemmat ehdot LICENSE-tiedostosta.
