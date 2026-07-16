"""Static reference data — country catalog used by rep-creation forms.

Kept as a plain in-memory list to avoid an extra dependency. The list follows
ISO 3166-1 alpha-2 codes and is prioritized around the primary Independent
Media Network operating regions. The full ISO catalog can be swapped in later
without changing the endpoint shape.
"""
from fastapi import APIRouter, Depends

from security import get_current_user

router = APIRouter(tags=["reference"])

COUNTRIES = [
    {"code": "FR", "name": "France"},
    {"code": "GB", "name": "United Kingdom"},
    {"code": "US", "name": "United States"},
    {"code": "CA", "name": "Canada"},
    {"code": "DE", "name": "Germany"},
    {"code": "ES", "name": "Spain"},
    {"code": "IT", "name": "Italy"},
    {"code": "NL", "name": "Netherlands"},
    {"code": "BE", "name": "Belgium"},
    {"code": "CH", "name": "Switzerland"},
    {"code": "AT", "name": "Austria"},
    {"code": "PT", "name": "Portugal"},
    {"code": "IE", "name": "Ireland"},
    {"code": "SE", "name": "Sweden"},
    {"code": "NO", "name": "Norway"},
    {"code": "DK", "name": "Denmark"},
    {"code": "FI", "name": "Finland"},
    {"code": "IS", "name": "Iceland"},
    {"code": "PL", "name": "Poland"},
    {"code": "CZ", "name": "Czech Republic"},
    {"code": "HU", "name": "Hungary"},
    {"code": "GR", "name": "Greece"},
    {"code": "TR", "name": "Türkiye"},
    {"code": "RO", "name": "Romania"},
    {"code": "BG", "name": "Bulgaria"},
    {"code": "HR", "name": "Croatia"},
    {"code": "SI", "name": "Slovenia"},
    {"code": "SK", "name": "Slovakia"},
    {"code": "EE", "name": "Estonia"},
    {"code": "LV", "name": "Latvia"},
    {"code": "LT", "name": "Lithuania"},
    {"code": "LU", "name": "Luxembourg"},
    {"code": "MT", "name": "Malta"},
    {"code": "CY", "name": "Cyprus"},
    {"code": "AE", "name": "United Arab Emirates"},
    {"code": "SA", "name": "Saudi Arabia"},
    {"code": "QA", "name": "Qatar"},
    {"code": "KW", "name": "Kuwait"},
    {"code": "BH", "name": "Bahrain"},
    {"code": "OM", "name": "Oman"},
    {"code": "IL", "name": "Israel"},
    {"code": "EG", "name": "Egypt"},
    {"code": "MA", "name": "Morocco"},
    {"code": "TN", "name": "Tunisia"},
    {"code": "ZA", "name": "South Africa"},
    {"code": "NG", "name": "Nigeria"},
    {"code": "KE", "name": "Kenya"},
    {"code": "AU", "name": "Australia"},
    {"code": "NZ", "name": "New Zealand"},
    {"code": "JP", "name": "Japan"},
    {"code": "KR", "name": "South Korea"},
    {"code": "SG", "name": "Singapore"},
    {"code": "HK", "name": "Hong Kong SAR"},
    {"code": "TW", "name": "Taiwan"},
    {"code": "TH", "name": "Thailand"},
    {"code": "MY", "name": "Malaysia"},
    {"code": "ID", "name": "Indonesia"},
    {"code": "PH", "name": "Philippines"},
    {"code": "VN", "name": "Vietnam"},
    {"code": "IN", "name": "India"},
    {"code": "BR", "name": "Brazil"},
    {"code": "AR", "name": "Argentina"},
    {"code": "MX", "name": "Mexico"},
    {"code": "CL", "name": "Chile"},
    {"code": "CO", "name": "Colombia"},
    {"code": "PE", "name": "Peru"},
]


@router.get("/countries")
async def list_countries(_: dict = Depends(get_current_user)):
    """Return the country catalog for rep-creation forms and editorial proposals.

    Available to any authenticated user — this is a static reference catalog
    with no sensitive data. Guarding the endpoint at all is purely to keep it
    off the public unauth surface.
    """
    return COUNTRIES
