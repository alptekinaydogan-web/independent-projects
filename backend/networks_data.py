"""Independent Media Network — inventory catalog.

Inventory is not sold country by country. It is sold as standardized advertising
products across the entire network (or an entire thematic sub-network).
"""

NETWORKS = [
    {
        "key": "global",
        "name": "Global Network",
        "tagline": "Every country site in the Independent Media Network.",
        "order": 0,
    },
    {
        "key": "tourism",
        "name": "Tourism Network",
        "tagline": "Every tourism-focused property across the network.",
        "order": 10,
    },
    {
        "key": "health",
        "name": "Health Network",
        "tagline": "Every health & wellness property across the network.",
        "order": 20,
    },
    {
        "key": "real_estate",
        "name": "Real Estate Network",
        "tagline": "Every real-estate property across the network.",
        "order": 30,
    },
    {
        "key": "education",
        "name": "Education Network",
        "tagline": "Every education & learning property across the network.",
        "order": 40,
    },
    {
        "key": "economy",
        "name": "Economy Network",
        "tagline": "Every economy & business property across the network.",
        "order": 50,
    },
    {
        "key": "sports",
        "name": "Sports Network",
        "tagline": "Every sports property across the network.",
        "order": 60,
    },
    {
        "key": "technology",
        "name": "Technology Network",
        "tagline": "Every technology property across the network.",
        "order": 70,
    },
    {
        "key": "entertainment",
        "name": "Entertainment Network",
        "tagline": "Every entertainment property across the network.",
        "order": 80,
    },
]

POSITIONS = [
    {"key": "hero",           "name": "Hero Banner",           "description": "Above the fold. Highest-impact placement on every home page.",       "order": 0},
    {"key": "header",         "name": "Header Banner",         "description": "Persistent header slot visible across the site.",                     "order": 10},
    {"key": "sidebar_top",    "name": "Sidebar Top",           "description": "Top of the primary sidebar on article and section pages.",           "order": 20},
    {"key": "sidebar_bottom", "name": "Sidebar Bottom",        "description": "Bottom of the primary sidebar — retention and conversion focus.",    "order": 30},
    {"key": "article_top",    "name": "Article Top",           "description": "Immediately below the article headline. Editorial-adjacent.",        "order": 40},
    {"key": "article_middle", "name": "Article Middle",        "description": "Mid-article inline placement, high dwell-time context.",              "order": 50},
    {"key": "article_bottom", "name": "Article Bottom",        "description": "End-of-article conversion slot.",                                    "order": 60},
    {"key": "footer",         "name": "Footer Banner",         "description": "Global footer banner across the network.",                            "order": 70},
    {"key": "mobile",         "name": "Mobile Banner",         "description": "Mobile-first placement optimized for phones and tablets.",           "order": 80},
    {"key": "sticky",         "name": "Sticky Banner",         "description": "Persistent sticky bar following the reader as they scroll.",         "order": 90},
]


def all_inventory():
    """Return the catalog as a flat list of network × position items.

    Each item has a deterministic id `{network_key}__{position_key}`, so that
    inventory selection in commercial proposals is stable across deploys.
    """
    items = []
    for net in NETWORKS:
        for pos in POSITIONS:
            items.append({
                "id": f"{net['key']}__{pos['key']}",
                "network_key": net["key"],
                "network_name": net["name"],
                "network_tagline": net["tagline"],
                "network_order": net["order"],
                "position_key": pos["key"],
                "position_name": pos["name"],
                "position_description": pos["description"],
                "position_order": pos["order"],
            })
    return items
