"""OE-only CMIS memory map for Bailly optical engines."""
from ..public.cmis import CmisMemMap


class BaillyOeMemMap(CmisMemMap):
    """OE-only CMIS pages; RLM pages belong to BaillyElsfpMemMap."""
