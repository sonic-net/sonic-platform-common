from ..public.cmis import CmisCodes

class CmisAec800gCodes(CmisCodes):
    TARGET_MODE = {
        0: 'local',
        1: 'remote-A',
        2: 'remote-B'
    }
