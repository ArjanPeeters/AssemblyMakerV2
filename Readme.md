# 🏗️ AssemblyMaker

Een Python-tool om automatisch `IfcElementAssembly`-objecten toe te voegen aan een IFC-bestand op basis van unieke waarden van een gekozen parameter.

---

## 🚀 Functie

Dit script:

1. Vraagt de gebruiker om een IFC-bestand te selecteren.
2. Vraagt om een **parameternaam** (zoals `"Brandwerendheid"` of `"Afwerking"`).
3. Doorzoekt het IFC-bestand en groepeert elementen per unieke waarde van deze parameter.
4. Voor elke waarde maakt het script een `IfcElementAssembly` aan met de bijbehorende elementen als children.
5. Slaat het aangepaste IFC-bestand op via een "Save As..." dialoog.

---

## 💻 Benodigdheden

- Python 3.9 of hoger
- [IfcOpenShell](https://ifcopenshell.org/)
- Tkinter (standaard inbegrepen bij Python)

Installeer de afhankelijkheden met:

```bash
pip install ifcopenshell

##eventueel eigen standalone .exe maken met auto-py-to-exe
pip install auto-py-to-exe
