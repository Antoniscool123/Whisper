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
