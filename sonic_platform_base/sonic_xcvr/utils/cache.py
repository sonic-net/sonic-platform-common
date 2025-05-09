from collections import abc

def read_only_cached_api_return(func):
    """Cache until func() returns a non-None, non-empty collections cache_value."""
    cache_name = f'_{func.__name__}_cache'
    def wrapper(self):
        if not hasattr(self, cache_name):
            cache_value = func(self)
            setattr(self, cache_name, cache_value)
        else:
            cache_value = getattr(self, cache_name)
            if cache_value is None or (isinstance(cache_value, abc.Iterable) and not cache_value):
                cache_value = func(self)
                setattr(self, cache_name, cache_value)
        return cache_value
    return wrapper
