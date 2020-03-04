from terraform import settings


class ResourceData(dict):
    def set_id(self, value: str):
        self[settings.ID_KEY] = value
