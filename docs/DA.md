# OpenFlow på dansk

OpenFlow er gratis, lokal diktering til Windows 10/11 (64-bit). Dansk er standardsprog, og du kan vælge mellem 100 Whisper-sprog. Ingen konto, abonnement, API-nøgle eller ordgrænse.

## Kom i gang

1. Hent `OpenFlow.exe` fra GitHub-releasen og læg den i en mappe, du ejer.
2. Start appen. Klik **Download model** for at hente den anbefalede Small-model (~181 MB). Det kræver internet én gang.
3. Tillad mikrofonen i **Windows Indstillinger → Privatliv og sikkerhed → Mikrofon**.
4. Klik i det program, hvor teksten skal indsættes.
5. Hold **højre Ctrl**, tal, og slip. OpenFlow skriver teksten lokalt.

Alternativt: klik mikrofonknappen, tal, og klik igen for at stoppe. **Ctrl+Alt+Space** slår håndfri diktering til/fra. **Ctrl+Alt+Escape** annullerer.

## Personligt ordforråd

Under **Vocabulary** kan du skrive erstatninger som:

```text
aarhus => Aarhus
anton => Anton
open flow => OpenFlow
```

Under **Settings** kan du slå fjernelse af tøven til (`øh`, `øhm`, `um`, `uh`) og vælge talte tegnsætningskommandoer som `punktum`, `komma`, `spørgsmålstegn` og `nyt afsnit`.

## Privatliv

Lyd behandles lokalt i hukommelsen og gemmes ikke som lydfil. Transskriptioner gemmes kun lokalt, hvis historik er slået til. Modeldownload sker fra det officielle Whisper.cpp-repository; ingen lyd eller tekst sendes til en server. Udklipsholderen bruges midlertidigt til at indsætte tekst, og andre udklipsholderprogrammer kan opbevare kopieret tekst.

## Bemærk

Appen er et selvstændigt, gratis alternativ inspireret af Wispr Flow-arbejdsgangen — ikke en officiel eller identisk kopi. Den indeholder ikke cloud-LLM-omskrivning eller skærmkontekst. Den er ikke kode-signeret; Windows SmartScreen kan derfor vise en advarsel. Kontrollér kildekode og SHA-256 før du vælger **Mere info → Kør alligevel**.

## Hastighed og præcision

- Vælg **Danish · Dansk** i stedet for automatisk sprogregistrering; så undgår du en ekstra beregning.
- For en i5-1145G7: start med **4 CPU threads** og lad **Preload** være slået til. Lad pc'en være tilsluttet strøm under længere optagelser.
- **Faster short recordings** i Settings bruger en kortere lydkontekst for optagelser på højst 26 sekunder. Det kan være hurtigere, men resultatet kan ændre sig. Slå det fra, hvis dansk bliver mindre præcist. Længere optagelser bruger altid fuld kontekst.
- **Small** er et kompromis. **Base** kan være hurtigere, men mindre præcis; **Medium** kan være mere præcis, men er langsommere og kræver mere hukommelse. Modeller skal downloades hver for sig.
- Tal tydeligt tæt på mikrofonen, undgå baggrundsstøj, og tilføj navne og fagord under **Vocabulary → Recognition hints**. Svag lyd forstærkes forsigtigt, men støj kan ikke fjernes automatisk.

I én automatiseret test med en 11-sekunders dansk prøve og Small-modellen tog fuld kontekst 7,80 sekunder og kort kontekst 3,19 sekunder på en GitHub Windows-runner. Resultatet var ikke identisk. Det er kun én prøve og ikke en måling på din computer; både hastighed og præcision varierer.
