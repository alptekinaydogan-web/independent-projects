"""ISO-2 country reference used across Independent Media Hub."""

COUNTRIES = [
    # Europe
    ("GB", "United Kingdom", "Europe"), ("DE", "Germany", "Europe"), ("FR", "France", "Europe"),
    ("IT", "Italy", "Europe"), ("ES", "Spain", "Europe"), ("NL", "Netherlands", "Europe"),
    ("SE", "Sweden", "Europe"), ("NO", "Norway", "Europe"), ("DK", "Denmark", "Europe"),
    ("FI", "Finland", "Europe"), ("PL", "Poland", "Europe"), ("PT", "Portugal", "Europe"),
    ("CH", "Switzerland", "Europe"), ("AT", "Austria", "Europe"), ("BE", "Belgium", "Europe"),
    ("IE", "Ireland", "Europe"), ("GR", "Greece", "Europe"), ("CZ", "Czech Republic", "Europe"),
    ("RO", "Romania", "Europe"), ("HU", "Hungary", "Europe"),
    # North America
    ("US", "United States", "North America"), ("CA", "Canada", "North America"),
    ("MX", "Mexico", "North America"),
    # South America
    ("BR", "Brazil", "South America"), ("AR", "Argentina", "South America"),
    ("CL", "Chile", "South America"), ("CO", "Colombia", "South America"),
    ("PE", "Peru", "South America"),
    # Asia
    ("JP", "Japan", "Asia"), ("CN", "China", "Asia"), ("IN", "India", "Asia"),
    ("KR", "South Korea", "Asia"), ("SG", "Singapore", "Asia"), ("TH", "Thailand", "Asia"),
    ("ID", "Indonesia", "Asia"), ("MY", "Malaysia", "Asia"), ("VN", "Vietnam", "Asia"),
    ("PH", "Philippines", "Asia"),
    # Middle East
    ("AE", "United Arab Emirates", "Middle East"), ("SA", "Saudi Arabia", "Middle East"),
    ("IL", "Israel", "Middle East"), ("TR", "Turkey", "Middle East"),
    ("QA", "Qatar", "Middle East"),
    # Africa
    ("ZA", "South Africa", "Africa"), ("NG", "Nigeria", "Africa"), ("EG", "Egypt", "Africa"),
    ("KE", "Kenya", "Africa"), ("MA", "Morocco", "Africa"),
    # Oceania
    ("AU", "Australia", "Oceania"), ("NZ", "New Zealand", "Oceania"),
]

DEFAULT_PRICES = {
    "North America": 42.0, "Europe": 35.0, "Oceania": 30.0,
    "Middle East": 28.0, "Asia": 22.0, "South America": 18.0, "Africa": 15.0,
}
