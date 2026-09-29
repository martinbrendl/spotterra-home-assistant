# Spotterra pro Home Assistant

**Co letí nad tvým domem — jako senzory v Home Assistantu.**

[Spotterra](https://spotterra.com) hlídá oblohu nad tvým místem: kolik letadel
je v okruhu, které z nich stojí za pohled (vzácný typ, vojenský transport,
stroj, který ti chybí ve sbírce), kdy ti něco přeletí nad hlavou a kdy jde
ISS. Tahle integrace to přenese do Home Assistantu — na ovládací panel,
do automatizací a (s Pro) i do reproduktoru.

> *English: Spotterra integration for Home Assistant — aircraft overhead,
> the next visible flyover, ISS passes and spoken alerts. Quick start in
> English is at the bottom.*

---

## Co to umí

- **Letadla nad domem** — počet v okruhu a seznam deseti nejbližších
  (volací znak, typ, registrace, vzdálenost, výška).
- **Zajímavá letadla** — vzácné typy, vojenské stroje, wishlist a typy,
  které ještě nemáš ve sbírce.
- **Příští přelet** — za kolik minut uvidíš další stroj a co to bude
  („Airbus A380", ne „A388"). Řadí se podle **času**, ne vzdálenosti:
  letadlo 5 km daleko, které odlétá, už nestihneš; 25 km daleko, které
  míří k tobě, máš za pár minut nad hlavou.
- **ISS** — začátek příštího viditelného průletu a jeho výška nad obzorem.
- **„Stojí za to jít ven"** — binární senzor pro automatizace
  (rozsviť lampičku, pošli notifikaci na hodinky…).
- **Hlášení do reproduktoru (Pro)** — hotová věta ve tvém jazyce
  s typem letadla a časem přeletu, připravená pro TTS.

## Co potřebuješ

- Home Assistant 2025.1 nebo novější a [HACS](https://hacs.xyz).
- Účet na [spotterra.com](https://spotterra.com) s nastaveným domovem
  (místo, odkud spotuješ — v Nastavení). Senzory fungují i v bezplatném účtu, hlášení do
  reproduktoru jsou součástí Spotterra Pro.

## Instalace

1. **HACS → ⋮ → Vlastní repozitáře.** Vlož
   `https://github.com/martinbrendl/spotterra-home-assistant`, typ
   **Integrace**, a klikni na *Přidat*.
2. V HACS vyhledej **Spotterra**, klikni na *Stáhnout* a **restartuj
   Home Assistant**.
3. Ve Spotterře otevři **Nastavení → Účet → Integrace Home Assistant →
   Vytvořit token**. Token se ukáže jen jednou — zkopíruj si ho.
4. V Home Assistantu: **Nastavení → Zařízení a služby → Přidat integraci
   → Spotterra**, vlož token a potvrď. Integrace token hned ověří
   a zařízení pojmenuje podle tvého domova.

Hotovo — za půl minuty uvidíš první hodnoty.

## Entity

`…` na začátku ID je název tvého místa (třeba `sensor.praha_6_letadla_nad_domem`).

| entita | co ukazuje |
|---|---|
| `sensor.…_letadla_nad_domem` | počet letadel v okruhu; v atributu `letadla` prvních deset |
| `sensor.…_zajimava_letadla` | kolik z nich stojí za pohled |
| `sensor.…_pristi_prelet_za` | za kolik minut uvidíš další stroj (0 = právě teď) |
| `sensor.…_pristi_prelet_stroj` | co to bude; v atributech volací znak, výška, směr, elevace |
| `sensor.…_nejzajimavejsi_ted` | nejzajímavější stroj v okruhu |
| `sensor.…_pristi_prulet_iss` | začátek příštího viditelného průletu ISS; v atributech věta pro reproduktor |
| `sensor.…_vyska_pristiho_pruletu_iss` | nejvyšší bod průletu nad obzorem (°) |
| `binary_sensor.…_nad_domem_je_neco_zajimaveho` | zapnuto, když je v okruhu něco zajímavého |
| `binary_sensor.…_tiche_hodiny` | běží tiché hodiny nastavené ve Spotterře |
| `event.…_hlaseni` | poslední hlášení (Pro) |

ISS senzor ukazuje *Neznámý*, když v příštích 36 hodinách není žádný
viditelný průlet nad 30° — ISS má viditelná období jen několik týdnů
v kuse, mezi nimi je to normální.

## Ovládací panel

V [`dashboards/spotterra.yaml`](dashboards/spotterra.yaml) je hotový panel
jen z vestavěných karet (nic dalšího z HACS nepotřebuje): počty, příští
přelet, tabulka strojů v okruhu, nejzajímavější stroj, ISS a graf dne.

1. **Nastavení → Ovládací panely → Přidat ovládací panel → Nový od nuly.**
2. Otevři ho, vpravo nahoře **✏️ → ⋮ → Editor YAML**, vlož obsah souboru.
3. Nahraď všechny výskyty `domov` názvem svého místa z ID entit
   (např. `praha_6`) a ulož.

## Hlásič do reproduktoru (Pro)

Importuj blueprint:

[![Otevřít v Home Assistantu](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmartinbrendl%2Fspotterra-home-assistant%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fspotterra%2Fhlasic.yaml)

…a vyber hlasovou službu a reproduktor. Umí hlásit jen když je někdo doma,
po hlášení vrátí hlasitost, jak byla, a drží rozestup mezi hlášeními.

- **Tiché hodiny se nastavují ve Spotterře** (Nastavení → Notifikace),
  ne v Home Assistantu — jinak by telefon mlčel a reproduktor hlásil.
- **Staré hlášení se neřekne.** Když byl Home Assistant offline, po
  startu neohlásí letadlo, které už dávno přeletělo (limit 15 minut).
- Vlastní automatizace můžeš postavit nad událostí `spotterra_udalost`;
  hotová věta je v `trigger.event.data.tts_text`.

## Příklad automatizace

Rozsviť lampu na zahradě, když letí něco zajímavého a je tma:

```yaml
automation:
  - alias: "Spotterra: něco zajímavého nad domem"
    triggers:
      - trigger: state
        entity_id: binary_sensor.domov_nad_domem_je_neco_zajimaveho
        to: "on"
    conditions:
      - condition: sun
        after: sunset
    actions:
      - action: light.turn_on
        target:
          entity_id: light.zahrada
```

## Soukromí a provoz

- Integrace se jednou za 30 sekund zeptá serveru Spotterry krátkým
  dotazem — žádné trvalé spojení.
- Token jde v hlavičce `Authorization`, nikdy v adrese. Zrušit ho můžeš
  kdykoli ve Spotterře; Home Assistant si pak řekne o nový a entity zůstanou.
- Poloha se z Home Assistantu nikam neposílá — Spotterra počítá z domova,
  který máš nastavený u sebe v účtu.

## Problémy

- **„Neplatný token"** — vytvoř ve Spotterře nový; Home Assistant sám
  nabídne opětovné ověření a nový token jen vložíš. Entity zůstanou.
- **Všechno ukazuje 0** — zkontroluj, že máš ve Spotterře nastavený domov.
- Chyby a nápady: [Issues](https://github.com/martinbrendl/spotterra-home-assistant/issues).

---

## Quick start (English)

1. **HACS → ⋮ → Custom repositories** → add
   `https://github.com/martinbrendl/spotterra-home-assistant` as
   *Integration*, download **Spotterra** and restart Home Assistant.
2. In Spotterra: **Settings → Account → Home Assistant integration →
   Create token** (shown once).
3. In Home Assistant: **Settings → Devices & services → Add integration →
   Spotterra**, paste the token.

You get sensors for aircraft in range, interesting aircraft, the next
visible flyover (sorted by *time*, not distance), the next visible ISS pass,
a binary sensor for automations and — with Spotterra Pro — spoken alerts via
the included blueprint. A ready-made dashboard is in
[`dashboards/spotterra.yaml`](dashboards/spotterra.yaml) (replace `domov`
with your entity prefix).

Data: aircraft positions come from community ADS-B networks, satellite
orbits from CelesTrak.

## Licence

[PolyForm Noncommercial 1.0.0](LICENSE) — pro osobní a nekomerční použití
zdarma: používej, upravuj a sdílej dál (s touto licencí a uvedením autora).
**Komerční použití není dovoleno** — kdo o něj stojí, ozvi se na
info@spotterra.com.

*License: PolyForm Noncommercial 1.0.0 — free for personal and other
noncommercial use; commercial use requires a separate agreement.*
