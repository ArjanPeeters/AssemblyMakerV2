import ifcopenshell
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from collections import defaultdict

def select_ifc_file():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(
        title="Selecteer een IFC-bestand",
        filetypes=[("IFC-bestanden", "*.ifc")]
    )

def save_ifc_file():
    root = tk.Tk()
    root.withdraw()
    return filedialog.asksaveasfilename(
        title="Sla het gewijzigde IFC-bestand op",
        defaultextension=".ifc",
        filetypes=[("IFC-bestanden", "*.ifc")]
    )

def main():
    # IFC-bestand selecteren
    ifc_path = select_ifc_file()
    if not ifc_path:
        return

    ifc = ifcopenshell.open(ifc_path)

    # Vraag om de parameternaam
    root = tk.Tk()
    root.withdraw()
    param_naam = simpledialog.askstring("Parameternaam", "Welke parameter wil je gebruiken om Assemblies te maken?")

    if not param_naam:
        return

    # Verzamel elementen gegroepeerd op parameterwaarde
    groepen = defaultdict(list)

    for rel in ifc.by_type("IfcRelDefinesByProperties"):
        prop_set = rel.RelatingPropertyDefinition
        for prop in getattr(prop_set, "HasProperties", []):
            if prop.Name == param_naam:
                waarde = str(prop.NominalValue.wrappedValue)
                for elem in rel.RelatedObjects:
                    groepen[waarde].append(elem)

    if not groepen:
        messagebox.showinfo("Geen elementen gevonden", f"Geen elementen gevonden met de parameter: {param_naam}")
        return

    # IFC context
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
            PredefinedType="USERDEFINEDp"
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

    # Opslaan
    save_path = save_ifc_file()
    if save_path:
        ifc.write(save_path)
        messagebox.showinfo("Succes", f"Assemblies aangemaakt op basis van '{param_naam}' en opgeslagen naar:\n{save_path}")
    else:
        print("Geen opslagpad gekozen. Bestand niet opgeslagen.")

if __name__ == "__main__":
    main()
