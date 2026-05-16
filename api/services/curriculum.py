"""Danish HF Curriculum Engine."""
from typing import Dict, List, Optional
from api.core.database import DatabaseManager


class CurriculumEngine:
    """Manages Danish HF curriculum objectives and mappings."""

    def __init__(self):
        self.db = DatabaseManager()
        self._init_curriculum()

    def _init_curriculum(self):
        """Initialize default curriculum data."""
        # Matematik C
        self._add_unit("matematik", "C", "funktioner", "Funktioner og modeller",
                      ["Lineære funktioner og modeller", "Procentregning og indekstal",
                       "Simple potens- og eksponentialfunktioner"],
                      ["Regne med variable", "Aflæse og tegne grafer"])
        self._add_unit("matematik", "C", "statistik", "Deskriptiv statistik",
                      ["Middelværdi, median, typetal", "Spredning, kvartilsæt",
                       "Søjle- og cirkeldiagrammer"],
                      ["Dataindsamling", "Tabel- og grafbehandling"])

        # Matematik B
        self._add_unit("matematik", "B", "differentialregning", "Differentialregning",
                      ["Den afledede funktion", "Tangent og monotoniforhold",
                       "Kædereglen", "Optimering"],
                      ["Funktioner", "Grænseværdi", "Sekant og tangent"])
        self._add_unit("matematik", "B", "vektorer", "Vektorer i planen",
                      ["Vektorer i koordinatsystemet", "Prikprodukt og vinkel",
                       "Parameterfremstilling for linje"],
                      ["Trigonometri", "Koordinatsystem"])
        self._add_unit("matematik", "B", "sandsynlighed", "Sandsynlighedsregning",
                      ["Kombinatorik", "Stokastiske variable",
                       "Binomialfordelingen"],
                      ["Procentregning", "Statistik"])
        self._add_unit("matematik", "B", "trigonometri", "Trigonometri",
                      ["Sin, cos, tan", "Enhedscirklen",
                       "Trekanter og beregninger"],
                      ["Funktioner", "Geometri"])

        # Matematik A
        self._add_unit("matematik", "A", "integralregning", "Integralregning",
                      ["Stamfunktioner", "Ubestemte og bestemte integraler",
                       "Arealberegning", "Rumfang ved rotation"],
                      ["Differentialregning", "Areal under kurve"])
        self._add_unit("matematik", "A", "differentialligninger", "Differentialligninger",
                      ["Førsteordens differentialligninger",
                       "Vækstmodeller", "Numeriske metoder"],
                      ["Integralregning", "Eksponentialfunktioner"])
        self._add_unit("matematik", "A", "hypotesetest", "Statistisk hypotesetest",
                      ["t-test", "Chi-i-anden-test", "Fortolkning af p-værdier"],
                      ["Statistik", "Sandsynlighed"])

        # Fysik C
        self._add_unit("fysik", "C", "mekanik", "Mekanik",
                      ["Bevægelse og hastighed", "Newtons love",
                       "Kraft og bevægelse", "Arbejde og energi"],
                      ["Matematiske funktioner"])
        self._add_unit("fysik", "C", "elektricitet", "Simpel elektricitet",
                      ["Strøm, spænding, modstand", "Ohms lov",
                       "Serie- og parallelforbindelser", "Effekt og energi"],
                      ["Matematiske ligninger"])

        # Fysik B
        self._add_unit("fysik", "B", "bolger", "Bølger",
                      ["Mekaniske bølger", "Lydbølger",
                       "Interferens og diffraktion", "Doppler-effekten"],
                      ["Mekanik", "Matematiske funktioner"])
        self._add_unit("fysik", "B", "termodynamik", "Termodynamik",
                      ["Temperatur og varme", "Tilstandsligningen",
                       "Arbejde i gasser", "Entropi og 2. lov"],
                      ["Energi", "Mekanik"])
        self._add_unit("fysik", "B", "atomfysik", "Atomfysik",
                      ["Bohrs atommodel", "Kvantespring",
                       "Spektrallinjer", "Radioaktivitet"],
                      ["Elektricitet", "Energi"])

        # Datalogi
        self._add_unit("datalogi", "C", "python_grundlag", "Python Grundlag",
                      ["Variabler og datatyper", "Betingelser og løkker",
                       "Funktioner", "Input og output"],
                      ["Matematisk logik"])
        self._add_unit("datalogi", "B", "datastrukturer", "Datastrukturer",
                      ["Lister og dictionaries", "Stakke og køer",
                       "Træer og grafer", "Filhåndtering"],
                      ["Python grundlag"])
        self._add_unit("datalogi", "B", "algoritmer", "Algoritmer",
                      ["Søgealgoritmer", "Sorteringsalgoritmer",
                       "Tidskompleksitet", "Rekursion"],
                      ["Datastrukturer", "Matematik"])
        self._add_unit("datalogi", "B", "it_sikkerhed", "IT-sikkerhed",
                      ["Kryptering", "Autentifikation",
                       "Sikkerhedsprincipper", "Privatliv"],
                      ["Netværk", "Programmering"])

        # Kommunikation
        self._add_unit("kommunikation", "C", "kommunikationsmodeller", "Kommunikationsmodeller",
                      ["Afsender-modtager-modellen", "Shannon-Weaver",
                       "Medier og kanaler", "Støj og forstyrrelser"],
                      [])
        self._add_unit("kommunikation", "B", "medieanalyse", "Medieanalyse",
                      ["Reklameanalyse", "Nyhedsmedier",
                       "Sociale medier", "Fake news"],
                      ["Kommunikationsmodeller"])
        self._add_unit("kommunikation", "B", "retorik", "Retorik",
                      ["Ethos, pathos, logos", "Retoriske virkemidler",
                       "Taleanalyse", "Argumentationstyper"],
                      ["Kommunikationsmodeller"])
        self._add_unit("kommunikation", "B", "argumentation", "Argumentation",
                      ["Argumenttyper", "Modargumenter",
                       "Ræsonnement og logik", "Overbevisning"],
                      ["Retorik"])
        self._add_unit("kommunikation", "A", "skriftlig_fremstilling", "Skriftlig fremstilling",
                      ["Kronik", "Essay", "Analyse",
                       "Formelle skriveregler"],
                      ["Medieanalyse", "Argumentation"])

    def _add_unit(self, subject: str, level: str, unit_id: str, title: str,
                  objectives: List[str], prerequisites: List[str]):
        """Add a curriculum unit."""
        # Store in memory palace as curriculum data
        content = f"""# {title} ({subject.upper()} {level})
## Læreplansmål
"""
        for obj in objectives:
            content += f"- {obj}\n"
        content += "\n## Forudsætninger\n"
        for prereq in prerequisites:
            content += f"- {prereq}\n"

        self.db.store_memory(
            content=content,
            wing="wing_fælles",
            room="room_læreplan",
            agent_id=subject,
            topic=unit_id,
            difficulty_level=level,
            memory_type="curriculum",
        )

    def get_objectives(self, topic: str) -> Optional[str]:
        """Get curriculum objectives for a topic."""
        results = self.db.search_memory(
            wing="wing_fælles",
            room="room_læreplan",
            topic=topic,
            limit=1
        )
        if results:
            return results[0].get("content", "")
        return None

    def get_subject_curriculum(self, subject: str, level: str = None) -> List[Dict]:
        """Get curriculum for a subject, optionally filtered by level."""
        results = self.db.search_memory(
            wing="wing_fælles",
            room="room_læreplan",
            agent_id=subject,
            limit=50
        )
        if level:
            results = [r for r in results if r.get("difficulty_level") == level]
        return results

    def get_all_topics(self) -> Dict[str, List[str]]:
        """Get all topics organized by subject."""
        subjects = ["matematik", "fysik", "datalogi", "kommunikation"]
        topics = {}
        for subject in subjects:
            results = self.db.search_memory(
                wing="wing_fælles",
                room="room_læreplan",
                agent_id=subject,
                limit=50
            )
            topics[subject] = [r.get("topic", "") for r in results if r.get("topic")]
        return topics
