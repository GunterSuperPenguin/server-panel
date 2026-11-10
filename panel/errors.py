class LocalizedError(Exception):
    def __init__(self, key, status=400, **params):
        super().__init__(key)
        self.key = key
        self.status = status
        self.params = params
