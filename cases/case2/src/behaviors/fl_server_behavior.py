from src.abstract.behavior.behavior import AbstractBehavior

from cases.case2.src.behaviors.cl_server_behavior import ClServerBehavior


class FlServerBehavior(AbstractBehavior):
    @staticmethod
    async def access_satellite(entity, data):
        await ClServerBehavior.access_satellite(entity=entity, data=data)
        return

    @staticmethod
    async def manage_round(entity, data):
        await entity.manage_fl_round()
        return
