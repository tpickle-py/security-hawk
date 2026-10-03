"""SVG sanitization — strips scripts, event handlers, and external references.

Uploaded SVG files pass through this before being stored or displayed,
preventing XSS and other injection attacks via malicious SVG content.
"""

from __future__ import annotations

import logging
import re
from xml.etree.ElementTree import register_namespace, tostring

from defusedxml.ElementTree import fromstring

logger = logging.getLogger(__name__)

# Register standard SVG namespaces to avoid ns0: prefixes
register_namespace("", "http://www.w3.org/2000/svg")
register_namespace("xlink", "http://www.w3.org/1999/xlink")

# Elements that can execute code or load external content
DANGEROUS_TAGS = frozenset(
    {
        "script",
        "foreignobject",
        "set",
        "animatetransform",
        "iframe",
        "object",
        "embed",
        "use",  # can reference external SVGs
    }
)

# Attributes that are event handlers (onclick, onload, etc.)
EVENT_ATTR_RE = re.compile(r"^on", re.IGNORECASE)

# Protocols that shouldn't appear in href/xlink:href
DANGEROUS_PROTOCOLS = frozenset({"javascript:", "data:text/html", "vbscript:"})


def _strip_namespace(tag: str) -> str:
    """Remove XML namespace prefix from a tag name."""
    if "}" in tag:
        return tag.split("}")[-1]
    return tag


def _clean_element(element) -> None:
    """Recursively remove dangerous elements and attributes."""
    for child in list(element):
        tag = _strip_namespace(child.tag).lower()

        if tag in DANGEROUS_TAGS:
            logger.debug("Removed dangerous element: <%s>", tag)
            element.remove(child)
            continue

        # Remove event handler attributes
        for attr in list(child.attrib):
            attr_name = _strip_namespace(attr).lower()

            if EVENT_ATTR_RE.match(attr_name):
                logger.debug("Removed event handler: %s", attr)
                del child.attrib[attr]
                continue

            # Check href values for dangerous protocols
            if attr_name in ("href", "xlink:href"):
                value = child.attrib[attr].strip().lower()
                if any(value.startswith(proto) for proto in DANGEROUS_PROTOCOLS):
                    logger.debug("Removed dangerous href: %s", value[:50])
                    del child.attrib[attr]

        _clean_element(child)


def sanitize_svg(svg_bytes: bytes) -> bytes:
    """Remove dangerous elements and attributes from SVG content.

    Args:
        svg_bytes: Raw SVG file content.

    Returns:
        Sanitized SVG as bytes (UTF-8 encoded).

    Raises:
        defusedxml.common.EntitiesForbidden: If the SVG contains XML bombs.
        xml.etree.ElementTree.ParseError: If the SVG is malformed.
    """
    tree = fromstring(svg_bytes)
    _clean_element(tree)

    result = tostring(tree, encoding="unicode")
    logger.info("Sanitized SVG (%d bytes input)", len(svg_bytes))
    return result.encode("utf-8")
