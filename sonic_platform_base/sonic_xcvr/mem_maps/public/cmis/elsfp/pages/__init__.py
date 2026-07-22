"""
    cmis.elsfp.pages package

    ELSFP-specific CMIS page classes (page 1Ah and page 1Bh).
"""

from .consts import (
    ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE,
    ELSFP_SETPOINTS_MON_PAGE,
)
from .page1a import ElsfpAdvertisementsFlagsCtrlPage
from .page1b import ElsfpSetpointsMonitorsPage

__all__ = [
    'ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE',
    'ELSFP_SETPOINTS_MON_PAGE',
    'ElsfpAdvertisementsFlagsCtrlPage',
    'ElsfpSetpointsMonitorsPage',
]
