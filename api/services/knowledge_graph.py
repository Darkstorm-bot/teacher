"""Knowledge Graph for concept relationships across subjects."""
from api.core.database import DatabaseManager


class KnowledgeGraph:
    """Manages concept nodes and prerequisite/cross-subject edges."""

    def __init__(self):
        self.db = DatabaseManager()

    def add_node(self, concept_id: str, subject: str, level: str,
                 display_name: str = None, description: str = None,
                 curriculum_ref: str = None):
        """Add a concept node to the graph."""
        if display_name is None:
            display_name = concept_id.replace("_", " ").title()
        self.db.add_concept_node(concept_id, subject, level, display_name,
                                  description, curriculum_ref)

    def add_edge(self, source_id: str, target_id: str, relation: str = "prerequisite",
                 weight: float = 1.0, cross_subject: bool = False):
        """Add an edge between two concepts."""
        self.db.add_concept_edge(source_id, target_id, relation, weight, cross_subject)

    def get_graph(self, subject: str = None):
        """Get the full graph or subject-filtered graph."""
        return self.db.get_concept_graph(subject)

    def get_prerequisites(self, concept_id: str):
        """Get prerequisite concepts for a given concept."""
        graph = self.db.get_concept_graph()
        prereqs = []
        for edge in graph["edges"]:
            if edge["target_id"] == concept_id and edge["relation"] == "prerequisite":
                for node in graph["nodes"]:
                    if node["id"] == edge["source_id"]:
                        prereqs.append(node)
                        break
        return prereqs

    def get_applications(self, concept_id: str):
        """Get concepts that this concept applies to."""
        graph = self.db.get_concept_graph()
        apps = []
        for edge in graph["edges"]:
            if edge["source_id"] == concept_id and edge["relation"] == "applies_to":
                for node in graph["nodes"]:
                    if node["id"] == edge["target_id"]:
                        apps.append(node)
                        break
        return apps

    def get_cross_subject_bridges(self, subject: str):
        """Get cross-subject connections for a subject."""
        graph = self.db.get_concept_graph()
        bridges = []
        for edge in graph["edges"]:
            if edge["cross_subject"]:
                for node in graph["nodes"]:
                    if node["id"] == edge["source_id"] and node["subject"] == subject:
                        for target in graph["nodes"]:
                            if target["id"] == edge["target_id"]:
                                bridges.append({
                                    "from": node,
                                    "to": target,
                                    "relation": edge["relation"]
                                })
                                break
                        break
        return bridges

    def update_mastery(self, concept_id: str, score: float):
        """Update mastery score for a concept."""
        # This is handled via mastery_scores table
        pass

    def init_default_graph(self):
        """Initialize the knowledge graph with Danish HF curriculum concepts."""
        # Matematik C
        self.add_node("funktioner", "matematik", "C", "Funktioner",
                     "Lineære funktioner, modeller og grafer")
        self.add_node("procentregning", "matematik", "C", "Procentregning",
                     "Procent, vækst, indekstal")
        self.add_node("deskriptiv_statistik", "matematik", "C", "Deskriptiv Statistik",
                     "Middelværdi, spredning, kvartiler")

        # Matematik B
        self.add_node("differentialregning", "matematik", "B", "Differentialregning",
                     "Afledede funktioner, tangenter, monotoni")
        self.add_node("vektorer_plan", "matematik", "B", "Vektorer i Planen",
                     "Vektorer, prikprodukt, parameterfremstilling")
        self.add_node("sandsynlighed", "matematik", "B", "Sandsynlighedsregning",
                     "Kombinatorik, stokastiske variable")
        self.add_node("trigonometri", "matematik", "B", "Trigonometri",
                     "Sin, cos, tan, enhedscirkel")

        # Matematik A
        self.add_node("integralregning", "matematik", "A", "Integralregning",
                     "Ubestemte og bestemte integraler, arealer")
        self.add_node("differentialligninger", "matematik", "A", "Differentialligninger",
                     "Førsteordens differentialligninger")
        self.add_node("vektorer_rum", "matematik", "A", "Vektorer i Rummet",
                     "Tre-dimensionale vektorer, krydsprodukt")
        self.add_node("hypotesetest", "matematik", "A", "Statistisk Hypotesetest",
                     "t-test, chi²-test")

        # Fysik C
        self.add_node("mekanik", "fysik", "C", "Mekanik",
                     "Bevægelse, kraft, Newtons love")
        self.add_node("energi", "fysik", "C", "Energi",
                     "Kinetisk energi, potentiel energi, energibevarelse")
        self.add_node("simpel_elektricitet", "fysik", "C", "Simpel Elektricitet",
                     "Strøm, spænding, modstand, Ohms lov")

        # Fysik B
        self.add_node("bolger", "fysik", "B", "Bølger",
                     "Mekaniske bølger, lydbølger, bølgeligning")
        self.add_node("termodynamik", "fysik", "B", "Termodynamik",
                     "Temperatur, varme, entropi")
        self.add_node("atomfysik", "fysik", "B", "Atomfysik",
                     "Bohrs atommodel, kvantespring")
        self.add_node("astrofysik", "fysik", "B", "Astrofysik",
                     "Stjerner, galakser, universet")

        # Datalogi
        self.add_node("python_grundlag", "datalogi", "C", "Python Grundlag",
                     "Variabler, løkker, betingelser, funktioner")
        self.add_node("datastrukturer", "datalogi", "B", "Datastrukturer",
                     "Lister, dicts, træer, grafer")
        self.add_node("algoritmer", "datalogi", "B", "Algoritmer",
                     "Søgning, sortering, kompleksitet")
        self.add_node("oop", "datalogi", "A", "Objektorienteret Programmering",
                     "Klasser, objekter, arv, polymorfi")
        self.add_node("it_sikkerhed", "datalogi", "B", "IT-sikkerhed",
                     "Kryptering, autentifikation, sikkerhedsprincipper")

        # Kommunikation
        self.add_node("kommunikationsmodeller", "kommunikation", "C", "Kommunikationsmodeller",
                     "Afsender-modtager, Shannon-Weaver")
        self.add_node("medieanalyse", "kommunikation", "B", "Medieanalyse",
                     "Reklamer, nyheder, sociale medier")
        self.add_node("retorik", "kommunikation", "B", "Retorik",
                     "Ethos, pathos, logos, retoriske virkemidler")
        self.add_node("argumentation", "kommunikation", "B", "Argumentation",
                     "Argumenttyper, modargumenter, ræsonnement")
        self.add_node("skriftlig_fremstilling", "kommunikation", "A", "Skriftlig Fremstilling",
                     "Kronik, essay, analyse")

        # Prerequisite edges
        self.add_edge("funktioner", "differentialregning", "prerequisite")
        self.add_edge("differentialregning", "integralregning", "prerequisite")
        self.add_edge("differentialregning", "differentialligninger", "prerequisite")
        self.add_edge("vektorer_plan", "vektorer_rum", "prerequisite")
        self.add_edge("trigonometri", "vektorer_plan", "prerequisite")
        self.add_edge("procentregning", "sandsynlighed", "prerequisite")
        self.add_edge("deskriptiv_statistik", "hypotesetest", "prerequisite")

        # Fysik prerequisites
        self.add_edge("mekanik", "bolger", "prerequisite")
        self.add_edge("energi", "termodynamik", "prerequisite")
        self.add_edge("simpel_elektricitet", "atomfysik", "prerequisite")

        # Datalogi prerequisites
        self.add_edge("python_grundlag", "datastrukturer", "prerequisite")
        self.add_edge("python_grundlag", "algoritmer", "prerequisite")
        self.add_edge("datastrukturer", "oop", "prerequisite")

        # Kommunikation prerequisites
        self.add_edge("kommunikationsmodeller", "medieanalyse", "prerequisite")
        self.add_edge("kommunikationsmodeller", "retorik", "prerequisite")
        self.add_edge("retorik", "argumentation", "prerequisite")
        self.add_edge("medieanalyse", "skriftlig_fremstilling", "prerequisite")
        self.add_edge("argumentation", "skriftlig_fremstilling", "prerequisite")

        # Cross-subject edges
        self.add_edge("differentialregning", "mekanik", "applies_to",
                       cross_subject=True)
        self.add_edge("python_grundlag", "mekanik", "applies_to",
                       cross_subject=True)
        self.add_edge("sandsynlighed", "it_sikkerhed", "applies_to",
                       cross_subject=True)
        self.add_edge("statistik", "medieanalyse", "applies_to",
                       cross_subject=True)
        self.add_edge("python_grundlag", "datastrukturer", "prerequisite")
