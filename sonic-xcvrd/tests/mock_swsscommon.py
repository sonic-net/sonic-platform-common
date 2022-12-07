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

    def hdel(self, key, field):
        if key not in self.mock_dict:
            return

        # swsscommon.FieldValuePairs
        fvs = self.mock_dict[key]
        for i, fv in enumerate(fvs):
            if fv[0] == field:
                del fvs[i]
                break
        if self.get_size_for_key(key) == 0:
            self._del(key)

    def set(self, key, fvs):
        self.mock_dict[key] = fvs
        self.mock_keys.append(key)
        pass

    def get(self, key):
        if key in self.mock_dict:
            return True, self.mock_dict[key]
        return False, None

    def get_size(self):
        return (len(self.mock_dict))

    def get_size_for_key(self, key):
        return len(self.mock_dict[key])

    def getKeys(self):
        return self.mock_keys
