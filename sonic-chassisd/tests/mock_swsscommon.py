STATE_DB = ''


class Table:
    def __init__(self, db, table_name):
        self.table_name = table_name
        self.mock_dict = {}

    def _del(self, key):
        if key in self.mock_dict:
            del self.mock_dict[key]
        pass

    def set(self, key, fvs):
        self.mock_dict[key] = fvs.fv_dict
        pass

    def get(self, key):
        if key in self.mock_dict:
            return self.mock_dict[key]
        return None

    def getKeys(self):
        return list(self.mock_dict)

    def size(self):
        return len(self.mock_dict)

class FieldValuePairs:
    def __init__(self, fvs):
        self.fv_dict = dict(fvs)
        pass
