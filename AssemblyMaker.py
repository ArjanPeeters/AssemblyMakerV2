import streamlit as st
import ifcopenshell
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
- Als meerdere elementen een classificatie delen, wordt die overgenomen op de Assembly
- Je downloadt het aangepaste bestand direct
""")

st.markdown("## 📤 Stap 1 – Upload een IFC-bestand")

uploaded_file = st.file_uploader("Klik hieronder om een IFC-bestand te selecteren", type=["ifc"], label_visibility="collapsed")

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_ifc:
        tmp_ifc.write(uploaded_file.read())
        tmp_ifc_path = tmp_ifc.name

    ifc = ifcopenshell.open(tmp_ifc_path)
    

    st.markdown("## 🧮 Stap 2 – Voer een parameternaam in")
    param_naam = st.text_input("Bijvoorbeeld: Brandwerendheid, Afwerking, Materiaal", placeholder="Typ hier de naam van de parameter")

    if param_naam:
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
                try:
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
                            AssemblyPlace="BUILDING",
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
                        
                        # 🧠 Classificatie verzamelen
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

                        # ✅ Meest voorkomende classificatie koppelen
                        if classification_counts:
                            meest_voorkomend = max(classification_counts, key=classification_counts.get)
                            classification_used = classification_objects.get(meest_voorkomend)

                            if classification_used and hasattr(classification_used, "is_a") and classification_used.is_a("IfcClassificationReference"):
                                # Gekoppelde classificatie is geldig
                                ifc.create_entity("IfcRelAssociatesClassification",
                                    GlobalId=ifcopenshell.guid.new(),
                                    OwnerHistory=owner_history,
                                    RelatedObjects=[assembly],
                                    RelatingClassification=classification_used
                                )
                            else:
                                # ⛑️ Fallback: maak een eigen classificatiereference aan
                                fallback_class = ifc.create_entity("IfcClassification",
                                    Source="AssemblyMaker",
                                    Edition="1.0",
                                    Name="AutoGenerated"
                                )

                                classification_ref = ifc.create_entity("IfcClassificationReference",
                                    Identification=f"{param_naam}-{waarde}",
                                    Name="Fallback",
                                    ReferencedSource=fallback_class
                                )

                                ifc.create_entity("IfcRelAssociatesClassification",
                                    GlobalId=ifcopenshell.guid.new(),
                                    OwnerHistory=owner_history,
                                    RelatedObjects=[assembly],
                                    RelatingClassification=classification_ref
                                )


                    # 💾 Bestand opslaan en download aanbieden
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

                except Exception as e:
                    st.error(f"Fout bij genereren assemblies: {e}")
