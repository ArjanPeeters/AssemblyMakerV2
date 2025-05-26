import streamlit as st
import ifcopenshell
import ifcopenshell.util.element
import tempfile
import os
from collections import defaultdict

st.set_page_config(page_title="AssemblyMaker", layout="centered")

st.title("🏗️ IFC AssemblyMaker")
st.markdown("""
Deze tool maakt automatisch één of meerdere **IfcElementAssembly**-objecten aan op basis van een parameter in een IFC-bestand.

### ✨ Wat doet deze tool?
- Je kiest een IFC-bestand
- Je voert de naam van een parameter in (zoals `Brandwerendheid`)
- Voor **elke unieke waarde** van die parameter maakt het script een eigen Assembly aan
- Je downloadt het aangepaste bestand direct

""")

st.markdown("## 📤 Stap 1 – Upload een IFC-bestand")

# Upload IFC-bestand knop
uploaded_file = st.file_uploader("Klik hieronder om een IFC-bestand te selecteren", type=["ifc"], label_visibility="collapsed")

if uploaded_file:
    # Tijdelijk bestand maken voor verwerking
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_ifc:
        tmp_ifc.write(uploaded_file.read())
        tmp_ifc_path = tmp_ifc.name

    # IFC-bestand openen
    ifc = ifcopenshell.open(tmp_ifc_path)

    st.markdown("## 🧮 Stap 2 – Voer een parameternaam in")
    param_naam = st.text_input("Bijvoorbeeld: Brandwerendheid, Afwerking, Materiaal", placeholder="Typ hier de naam van de parameter")

    if param_naam:
        # Zoek elementen op basis van parameterwaarde
        groepen = defaultdict(list)

        for rel in ifc.by_type("IfcRelDefinesByProperties"):
            prop_set = rel.RelatingPropertyDefinition
            for prop in getattr(prop_set, "HasProperties", []):
                if prop.Name == param_naam:
                    waarde = str(prop.NominalValue.wrappedValue)
                    for elem in rel.RelatedObjects:
                        groepen[waarde].append(elem)

        if not groepen:
            st.warning(f"Geen elementen gevonden met parameternaam '{param_naam}'.")
        else:
            st.success(f"Gevonden waarden voor '{param_naam}': {', '.join(groepen.keys())}")
            st.markdown("## 🏗️ Stap 3 – Maak Assemblies aan")

            if st.button("🔧 Assemblies genereren"):
                project = ifc.by_type("IfcProject")[0]
                site = ifc.by_type("IfcSite")[0]
                owner_history = ifc.by_type("IfcOwnerHistory")[0]

                for waarde, elementen in groepen.items():
                    assembly = ifc.create_entity("IfcElementAssembly",
                        GlobalId=ifcopenshell.guid.new(),
                        OwnerHistory=owner_history,
                        Name=f"{param_naam}: {waarde}",
                        ObjectType="Assembly",
                        ObjectPlacement=site.ObjectPlacement,
                        Representation=None,
                        AssemblyPlace="SITE",
                        PredefinedType="USERDEFINED"
                    )

                    ifc.create_entity("IfcRelAggregates",
                        GlobalId=ifcopenshell.guid.new(),
                        OwnerHistory=owner_history,
                        RelatingObject=site,
                        RelatedObjects=[assembly]
                    )

                    ifc.create_entity("IfcRelAggregates",
                        GlobalId=ifcopenshell.guid.new(),
                        OwnerHistory=owner_history,
                        RelatingObject=assembly,
                        RelatedObjects=elementen
                    )

                # Tijdelijk bestand maken om te downloaden
                result_path = tmp_ifc_path.replace(".ifc", "_assemblies.ifc")
                ifc.write(result_path)

                with open(result_path, "rb") as f:
                    st.markdown("## 💾 Stap 4 – Download je aangepaste bestand")
                    st.download_button(
                        label="📥 Download aangepast IFC-bestand",
                        data=f,
                        file_name=os.path.basename(result_path),
                        mime="application/octet-stream"
                    )
