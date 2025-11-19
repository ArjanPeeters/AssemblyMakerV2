import streamlit as st
import ifcopenshell
from ifcopenshell import guid
import tempfile
import os
from collections import defaultdict

st.set_page_config(page_title="Assembly / Zone / System Maker", layout="centered")

st.title("🏗️ IFC Grouper: Assemblies, Zones & Systems")

st.markdown("""
Deze tool groepeert **specifieke typen elementen** in een IFC-bestand op basis van een **parameterwaarde**, en maakt daar:

- `IfcElementAssembly` (voor bouwkundige elementen, onder het gebouw),
- `IfcZone` (voor ruimtes / IfcSpace), of
- `IfcSystem` (voor installatie-elementen / IfcDistributionElement)

voor aan, afhankelijk van je keuze.

> Let op: we gebruiken nog steeds **één property als grouping key**. Dat is een pragmatische keuze, geen perfecte semantische waarheid.
""")

st.markdown("## 📤 Stap 1 – Upload een IFC-bestand")
uploaded_file = st.file_uploader("Klik hieronder om een IFC-bestand te selecteren", type=["ifc"])

# IFC-model in session_state bewaren, zodat meerdere acties op hetzelfde model worden uitgevoerd
if uploaded_file is not None:
    if "ifc" not in st.session_state or st.session_state.get("uploaded_name") != uploaded_file.name:
        data = uploaded_file.getvalue()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_ifc:
            tmp_ifc.write(data)
            tmp_ifc_path = tmp_ifc.name

        ifc = ifcopenshell.open(tmp_ifc_path)
        st.session_state["ifc"] = ifc
        st.session_state["uploaded_name"] = uploaded_file.name
        st.session_state["actions_log"] = []
    else:
        ifc = st.session_state["ifc"]

if uploaded_file and "ifc" in st.session_state:
    ifc = st.session_state["ifc"]

    st.markdown("## ⚙️ Stap 2 – Kies wat je wilt aanmaken")

    mode = st.radio(
        "Wat wil je op basis van een parameterwaarde maken?",
        [
            "Assemblies (IfcElementAssembly voor bouwkundige elementen)",
            "Zones (IfcZone voor ruimtes / IfcSpace)",
            "Systems (IfcSystem voor installatie-elementen / IfcDistributionElement)",
        ]
    )

    # Uitleg per mode
    if mode.startswith("Assemblies"):
        st.info("Assemblies: we groeperen alleen **IfcBuildingElement**-elementen (wanden, vloeren, kolommen, etc.).")
    elif mode.startswith("Zones"):
        st.info("Zones: we groeperen alleen **IfcSpace**-elementen (ruimtes) in IfcZone-groepen.")
    elif mode.startswith("Systems"):
        st.info("Systems: we groeperen alleen **IfcDistributionElement**-elementen (MEP / installatie).")

    st.markdown("## 🧮 Stap 3 – Parameternaam")
    param_naam = st.text_input(
        "Welke parameter moet gebruikt worden om te groeperen?",
        placeholder="Bijvoorbeeld: Brandwerendheid, ZoneNaam, Systeemcode"
    )

    def group_by_property_filtered(ifc_file, property_name, filter_fn):
        """Zoek elementen gegroepeerd op waarde van een gegeven property, met type-filter."""
        groepen_local = defaultdict(list)
        for rel in ifc_file.by_type("IfcRelDefinesByProperties"):
            prop_set = rel.RelatingPropertyDefinition
            for prop in getattr(prop_set, "HasProperties", []):
                if prop.Name == property_name and hasattr(prop, "NominalValue"):
                    waarde = str(prop.NominalValue.wrappedValue)
                    for elem in rel.RelatedObjects:
                        if filter_fn(elem):
                            groepen_local[waarde].append(elem)
        return groepen_local

    # Filterfunctie kiezen per mode
    def assembly_filter(elem):
        return elem.is_a("IfcBuildingElement")

    def zone_filter(elem):
        return elem.is_a("IfcSpace")

    def system_filter(elem):
        # Alles wat IfcDistributionElement of subtype is
        return elem.is_a("IfcDistributionElement")

    if param_naam:
        if mode.startswith("Assemblies"):
            groepen = group_by_property_filtered(ifc, param_naam, assembly_filter)
        elif mode.startswith("Zones"):
            groepen = group_by_property_filtered(ifc, param_naam, zone_filter)
        elif mode.startswith("Systems"):
            groepen = group_by_property_filtered(ifc, param_naam, system_filter)
        else:
            groepen = {}

        if not groepen:
            st.warning(f"Geen elementen gevonden met parameternaam '{param_naam}' binnen het gefilterde type voor deze mode.")
        else:
            st.success(f"Gevonden waarden voor '{param_naam}': {', '.join(groepen.keys())}")

            st.markdown("## 🏗️ Stap 4 – Actie uitvoeren")

            if st.button("🔧 Uitvoeren voor huidige keuze"):
                try:
                    owner_history_list = ifc.by_type("IfcOwnerHistory")
                    owner_history = owner_history_list[0] if owner_history_list else None

                    if mode.startswith("Assemblies"):
                        buildings = ifc.by_type("IfcBuilding")
                        if not buildings:
                            st.error("Geen IfcBuilding gevonden in dit model. Assemblies kunnen niet geplaatst worden.")
                        else:
                            building = buildings[0]

                            for waarde, elementen in groepen.items():
                                assembly = ifc.create_entity(
                                    "IfcElementAssembly",
                                    GlobalId=guid.new(),
                                    OwnerHistory=owner_history,
                                    Name=f"{param_naam}: {waarde}",
                                    ObjectType="Assembly",
                                    ObjectPlacement=building.ObjectPlacement,
                                    Representation=None,
                                    AssemblyPlace="SITE",
                                    PredefinedType="USERDEFINED",
                                )

                                # Assembly onder het gebouw hangen
                                ifc.create_entity(
                                    "IfcRelAggregates",
                                    GlobalId=guid.new(),
                                    OwnerHistory=owner_history,
                                    RelatingObject=building,
                                    RelatedObjects=[assembly],
                                )

                                # Elementen onder de assembly hangen
                                ifc.create_entity(
                                    "IfcRelAggregates",
                                    GlobalId=guid.new(),
                                    OwnerHistory=owner_history,
                                    RelatingObject=assembly,
                                    RelatedObjects=elementen,
                                )

                                # Meest voorkomende classificatie van elementen naar assembly kopiëren
                                classification_counts = {}
                                classification_objects = {}

                                for rel in ifc.by_type("IfcRelAssociatesClassification"):
                                    for related in rel.RelatedObjects:
                                        if related in elementen:
                                            item = rel.RelatingClassification
                                            if not item:
                                                continue
                                            key = getattr(item, "Identification", None) or getattr(item, "Name", None)
                                            if key:
                                                classification_counts[key] = classification_counts.get(key, 0) + 1
                                                classification_objects[key] = item

                                if classification_counts:
                                    meest_voorkomend = max(classification_counts, key=classification_counts.get)
                                    classification_used = classification_objects.get(meest_voorkomend)

                                    if classification_used and hasattr(classification_used, "is_a"):
                                        ifc.create_entity(
                                            "IfcRelAssociatesClassification",
                                            GlobalId=guid.new(),
                                            OwnerHistory=owner_history,
                                            RelatedObjects=[assembly],
                                            RelatingClassification=classification_used,
                                        )

                            st.session_state["actions_log"].append(f"Assemblies gemaakt op basis van '{param_naam}' (alleen IfcBuildingElement)")

                    elif mode.startswith("Zones"):
                        # Zones voor IfcSpace
                        for waarde, elementen in groepen.items():
                            zone = ifc.create_entity(
                                "IfcZone",
                                GlobalId=guid.new(),
                                OwnerHistory=owner_history,
                                Name=f"{param_naam}: {waarde}",
                                Description=None,
                            )

                            ifc.create_entity(
                                "IfcRelAssignsToGroup",
                                GlobalId=guid.new(),
                                OwnerHistory=owner_history,
                                RelatedObjects=elementen,
                                RelatingGroup=zone,
                            )

                        st.session_state["actions_log"].append(f"Zones gemaakt op basis van '{param_naam}' (alleen IfcSpace)")

                    elif mode.startswith("Systems"):
                        # Systems voor IfcDistributionElement
                        for waarde, elementen in groepen.items():
                            system = ifc.create_entity(
                                "IfcSystem",
                                GlobalId=guid.new(),
                                OwnerHistory=owner_history,
                                Name=f"{param_naam}: {waarde}",
                                Description=None,
                            )

                            ifc.create_entity(
                                "IfcRelAssignsToGroup",
                                GlobalId=guid.new(),
                                OwnerHistory=owner_history,
                                RelatedObjects=elementen,
                                RelatingGroup=system,
                            )

                        st.session_state["actions_log"].append(f"Systems gemaakt op basis van '{param_naam}' (alleen IfcDistributionElement)")

                    st.success("Actie uitgevoerd. Je kunt nu eventueel een andere mode kiezen en nogmaals uitvoeren.")
                except Exception as e:
                    st.error(f"Fout bij uitvoeren van de actie: {e}")

    # Overzicht van wat er al gebeurd is
    if st.session_state.get("actions_log"):
        st.markdown("### ✅ Uitgevoerde acties in deze sessie:")
        for entry in st.session_state["actions_log"]:
            st.write(f"- {entry}")

    st.markdown("## 💾 Stap 5 – Download aangepast IFC-bestand")

    if st.button("📥 Genereer downloadbestand"):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_out:
                out_path = tmp_out.name
                st.session_state["ifc"].write(out_path)

            with open(out_path, "rb") as f:
                st.download_button(
                    label="📥 Download IFC met alle wijzigingen",
                    data=f,
                    file_name=f"{os.path.splitext(st.session_state['uploaded_name'])[0]}_modified.ifc",
                    mime="application/octet-stream",
                )
        except Exception as e:
            st.error(f"Fout bij schrijven/aanbieden van het IFC-bestand: {e}")
