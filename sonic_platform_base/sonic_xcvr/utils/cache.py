def read_only_cached_api_return(func):
    """Cache until func() returns a non-None, non-empty dict/list value."""
    cache_name = f'_{func.__name__}_cache'
    def wrapper(self):
        if not hasattr(self, cache_name):
            val = func(self)
            setattr(self, cache_name, val)
        else:
            val = getattr(self, cache_name)
            if val is None or (isinstance(val, (dict, list)) and len(val) == 0):
                val = func(self)
                setattr(self, cache_name, val)
        return val
    return wrapper