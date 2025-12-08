"""
Standard Vaccination Schedule for Broilers in Kenya.
"""

STANDARD_SCHEDULE = [
    {
        "day": 1,
        "vaccine_name": "Marek's Disease",
        "disease_target": "Marek's Disease",
        "method": "injection",
        "notes": "Usually administered at hatchery."
    },
    {
        "day": 7,
        "vaccine_name": "Newcastle Disease (Hitchner B1)",
        "disease_target": "Newcastle Disease",
        "method": "eye_drop",
        "notes": "First dose."
    },
    {
        "day": 14,
        "vaccine_name": "Gumboro (IBD) - Intermediate",
        "disease_target": "Infectious Bursal Disease",
        "method": "drinking_water",
        "notes": "First dose."
    },
    {
        "day": 18,
        "vaccine_name": "Newcastle Disease (LaSota)",
        "disease_target": "Newcastle Disease",
        "method": "drinking_water",
        "notes": "Booster dose."
    },
    {
        "day": 21,
        "vaccine_name": "Gumboro (IBD) - Hot",
        "disease_target": "Infectious Bursal Disease",
        "method": "drinking_water",
        "notes": "Booster dose."
    },
    {
        "day": 28,
        "vaccine_name": "Newcastle Disease (Komarov)",
        "disease_target": "Newcastle Disease",
        "method": "drinking_water",
        "notes": "Second booster."
    },
     {
        "day": 35,
        "vaccine_name": "Fowl Pox",
        "disease_target": "Fowl Pox",
        "method": "spray",
        "notes": "Wing web stab or spray."
    }
]
