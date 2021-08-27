from .sff8024 import Sff8024

class CmisCodes(Sff8024):
    POWER_CLASSES = {
        0: "Power Class 1",
        1: "Power Class 2",
        2: "Power Class 3",
        3: "Power Class 4",
        4: "Power Class 5",
        5: "Power Class 6",
        6: "Power Class 7",
        7: "Power Class 8"
    }

    MEDIA_TYPES = {
        0: "Undefined",
        1: "nm_850_media_interface",
        2: "sm_media_interface",
        3: "passive_copper_media_interface",
        4: "active_cable_media_interface",
        5: "base_t_media_interface",
    }
