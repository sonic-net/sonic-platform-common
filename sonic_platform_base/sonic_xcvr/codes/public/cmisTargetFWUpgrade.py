from .cmis import CmisCodes

class CmisTargetFWUpgradeCodes(CmisCodes):
    TARGET_MODE = {
        0: 'local',
        1: 'remote-A',
        2: 'remote-B'
    }
