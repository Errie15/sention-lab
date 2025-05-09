# SENTION - Glukosanalys

Ett webbaserat verktyg för analys av glukosdata från kontinuerliga glukosmätningar (CGM).

## Funktioner

- **Filuppladdning**: Ladda upp CSV-filer med glukosdata för analys
- **Omfattande Analys**: Beräknar bl.a. genomsnittligt glukos, eHbA1C, glukosvariabilitet och tidsfördelning
- **Episodidentifiering**: Identifierar och analyserar låga, höga och mycket höga glukosepisoder
- **Excel-exportering**: Möjlighet att ladda ner analysresultaten i Excel-format
- **Visuell Presentation**: Tydlig och användarvänlig presentation av analysresultat

## Installation

1. Klona repositoryt:
```
git clone https://github.com/[användarnamn]/SENTION.git
cd SENTION
```

2. Skapa en virtuell miljö och installera beroenden:
```
python -m venv venv
venv\Scripts\activate  # På Windows
pip install -r requirements.txt
```

3. Starta applikationen:
```
python app.py
```

4. Öppna applikationen i webbläsaren: `http://localhost:5000`

## Teknisk Översikt

- **Backend**: Python med Flask
- **Datahantering**: Pandas för dataanalys
- **Exportering**: XlsxWriter för Excel-generering
- **Frontend**: HTML, CSS och JavaScript

## Dataanalys

Applikationen utför följande typer av analyser:
- Generell statistik (genomsnitt, eHbA1C, variabilitet)
- Tidsfördelning mellan olika glukosnivåer
- Identifiering och analys av glukosepisoder
- Beräkning av medelduration för episoder

## Licens

[Lägg till licens information här]
