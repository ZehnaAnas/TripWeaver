VALID_CITIES = [
    'Bali', 'Bangkok', 'Beijing', 'Busan', 'Cebu', 'Delhi', 'Guangzhou', 
    'Hanoi', 'Ho Chi Minh City', 'Jakarta', 'Kuala Lumpur', 'Manila', 
    'Mumbai', 'Osaka', 'Penang', 'Phuket', 'Seoul', 'Shanghai', 
    'Singapore', 'Tokyo'
]

VALID_AIRPORTS = [
    'BKK', 'BOM', 'CAN', 'CGK', 'DEL', 'DPS', 'HAN', 'HKT', 'ICN', 
    'KIX', 'KUL', 'MNL', 'NRT', 'PEK', 'PEN', 'PUS', 'PVG', 'SGN', 'SIN'
]

CITY_TO_AIRPORT = {
    'Bali': 'DPS',
    'Bangkok': 'BKK',
    'Beijing': 'PEK',
    'Busan': 'PUS',
    'Cebu': 'CEB',
    'Delhi': 'DEL',
    'Guangzhou': 'CAN',
    'Hanoi': 'HAN',
    'Ho Chi Minh City': 'SGN',
    'Jakarta': 'CGK',
    'Kuala Lumpur': 'KUL',
    'Manila': 'MNL',
    'Mumbai': 'BOM',
    'Osaka': 'KIX',
    'Penang': 'PEN',
    'Phuket': 'HKT',
    'Seoul': 'ICN',
    'Shanghai': 'PVG',
    'Singapore': 'SIN',
    'Tokyo': 'NRT'
}

COUNTRY_TO_CITIES =  {"indonesia": ["Bali", "Jakarta"],
    "thailand": ["Bangkok", "Phuket"],
    "china": ["Beijing", "Guangzhou", "Shanghai"],
    "south korea": ["Busan", "Seoul"],
    "korea": ["Busan", "Seoul"],
    "philippines": ["Cebu", "Manila"],
    "india": ["Delhi", "Mumbai"],
    "vietnam": ["Hanoi", "Ho Chi Minh City"],
    "malaysia": ["Kuala Lumpur", "Penang"],
    "japan": ["Osaka", "Tokyo"],
    "singapore": ["Singapore"],
}