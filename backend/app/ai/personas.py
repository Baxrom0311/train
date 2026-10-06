class MentorPersona:
    def __init__(self, name: str, sector: str, system_prompt: str):
        self.name = name
        self.sector = sector
        self.system_prompt = system_prompt

IT_MENTOR = MentorPersona(
    name="Alex",
    sector="IT",
    system_prompt="You are Alex, an expert IT mentor."
)
FINANCE_MENTOR = MentorPersona(
    name="Sarah",
    sector="Banking",
    system_prompt="You are Sarah, an expert Banking mentor."
)
