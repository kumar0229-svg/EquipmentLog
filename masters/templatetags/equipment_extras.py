"""Template filter mapping an equipment type's name to its dashboard icon.

Equipment type names are free text (see masters.models.EquipmentType), so the
match is done on a normalised slug rather than a fixed choice list. New
equipment types silently fall back to no icon instead of erroring.
"""
import re

from django import template
from django.templatetags.static import static

register = template.Library()

# Equipment types whose seeded/likely name doesn't slugify to the matching
# icon file (e.g. a naming mismatch between the equipment type and the
# design export it was drawn from).
ALIASES = {
    'anfd': 'afnd',  # Agitated Nutsche Filter Dryer — icon file is named AFND
}

ICON_SLUGS = {
    'afnd',
    'aod-pump',
    'candle-filter',
    'centrifuge',
    'co-mill',
    'isolator',
    'jet-mill',
    'multi-mill',
    'nutsche-filter',
    'reactor',
    'sifter',
    'vacuum-tray-drier',
    'vessels',
}

_NON_ALNUM = re.compile(r'[^a-z0-9]+')


def _slugify(name):
    return _NON_ALNUM.sub('-', name.strip().lower()).strip('-')


@register.simple_tag
def equipment_icon_url(equipment_type_name):
    """Static URL for this equipment type's icon, or '' if none matches."""
    slug = _slugify(equipment_type_name or '')
    slug = ALIASES.get(slug, slug)
    if slug not in ICON_SLUGS:
        return ''
    return static(f'icons/svg/{slug}.svg')
