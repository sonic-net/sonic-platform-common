from collections import namedtuple


def disk_partitions():
    sdiskio = namedtuple('sdiskio', ['read_count', 'write_count'])
    return sdiskio(read_count=42444, write_count=210141)
