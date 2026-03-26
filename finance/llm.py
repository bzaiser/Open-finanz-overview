import random

def get_pension_forecast():
    """
    Simulates calling a free LLM to get the latest pension adjustment forecast.
    Prompt: „Nenne mir die aktuelle Prognose für die Rentenanpassung 2026 laut dem jüngsten Rentenversicherungsbericht des BMAS.“
    """
    # Mock response
    return {
        "text": "Laut aktuellen Prognosen wird für 2026 eine Rentenanpassung von ca. 3,5% erwartet.",
        "value": 3.5,
        "source": "Simulated LLM Response"
    }

def get_inflation_forecast():
    """
    Simulates calling a free LLM to get the current inflation rate forecast.
    Prompt: „Wie hoch schätzt das Statistische Bundesamt die Inflationsrate für das aktuelle Jahr?“
    """
    # Mock response
    return {
        "text": "Die Inflationsrate für das aktuelle Jahr wird auf etwa 2,2% geschätzt.",
        "value": 2.2,
        "source": "Simulated LLM Response"
    }
