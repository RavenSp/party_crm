

def name_normalizer(name: str) -> str:
    return name.replace(' ', '')\
        .replace('.', '')\
        .replace(',','')\
        .replace(':', '')\
        .replace('!', '') \
        .replace('?', '') \
        .replace('%', '') \
        .replace('_', '') \
        .replace('-', '') \
        .replace('*', '')\
        .lower()

