from custom_components.smarthashtag.sensor import ENTITY_CLIMATE_DESCRIPTIONS

for i in ENTITY_CLIMATE_DESCRIPTIONS:
    print(
        f"""      }},
      "{i.key}": {{
        "name": "{i.name}"
        """
    )
