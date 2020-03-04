import asyncio
import collections
import logging
import os
import sys
import typing

from terraform import settings

logger = logging.getLogger(__name__)


class BaseResource:
    name: str


class Resource(BaseResource):
    ...


class DataSource(BaseResource):
    ...


class Resources(collections.abc.Mapping):
    def __init__(
        self, resources: typing.Optional[typing.Sequence[BaseResource]] = None
    ):
        self.resources = [] if resources is None else list(resources)

    def __getitem__(self, name):
        for resource in self.resources:
            if resource.name == name:
                return resource
        raise KeyError(name)

    def __iter__(self):
        return iter(self.resources)

    def __len__(self):
        return len(self.resources)

    def add(self, resource: BaseResource):
        self.resources.append(resource)


class Provider:
    name: str

    def __init__(
        self,
        resources: typing.Optional[typing.Sequence[Resource]] = None,
        data_sources: typing.Optional[typing.Sequence[DataSource]] = None,
    ):
        self.resources = Resources(resources)
        self.data_sources = Resources(data_sources)

    def add_resource(self, resource: Resource):
        self.resources.add(resource)

    def add_data_source(self, data_source: DataSource):
        self.data_sources.add(data_source)


async def run_server(*, provider: Provider):
    if os.getenv(settings.MAGIC_COOKIE_KEY) != settings.MAGIC_COOKIE_VALUE:
        logger.error(
            "This is a Terraform plugin. "
            "These are not meant to be executed directly."
        )
        sys.exit(1)

    min_port = int(os.getenv("PLUGIN_MIN_PORT") or 0)
    max_port = int(os.getenv("PLUGIN_MAX_PORT") or 0)
    if min_port > max_port:
        logger.error("PLUGIN_MIN_PORT value is greater than PLUGIN_MAX_PORT value")
        sys.exit(1)


def run(*, provider: Provider):
    asyncio.run(run_server(provider=provider))
