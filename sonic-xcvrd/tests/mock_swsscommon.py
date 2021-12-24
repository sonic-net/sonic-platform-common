STATE_DB = ''
CHASSIS_STATE_DB = ''


class Table:
    def __init__(self, db, table_name):
        self.table_name = table_name
        self.mock_dict = {}
        self.mock_keys = []

    def _del(self, key):
        if key in self.mock_dict:
            del self.mock_dict[key]
            self.mock_keys.remove(key)
        pass

    def set(self, key, fvs):
        self.mock_dict[key] = fvs
        self.mock_keys.append(key)
        pass

    def get(self, key):
        if key in self.mock_dict:
            return self.mock_dict[key]
        return None

    def get_size(self):
        return (len(self.mock_dict))
    
    def getKeys(self):
        return self.mock_keys


class FieldValuePairs:
    def __init__(self, fvs):
        self.fv_dict = dict(fvs)
        pass
