import asyncio
from src.abstract.entity.entity_cluster import AbstractEntityCluster


class Ground(AbstractEntityCluster):
    def __init__(self, cluster_category):
        super().__init__(cluster_category)

    async def start_behaviors(self):
        await asyncio.gather(
            self.common_behavior(),
        )

    async def common_behavior(self):
        pass

