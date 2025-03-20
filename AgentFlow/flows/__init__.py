from ..data_model import flowDetailParam, FlowTypeEnum
from .loop_flow import SequentialLoopFlow, AutoSchedLoopFlow
from .sequential_flow import SequentialFlow
from .auto_sched_flow import AutoSchedFlow
from .base_flow import BaseFlow

from typing import Union, Dict

class FlowFactory:
    @staticmethod
    def create_flow(flow_type: str, config: Union[Dict, flowDetailParam]) -> BaseFlow:
        if flow_type == FlowTypeEnum.SEQUENTIAL:
            return SequentialFlow(config)
        elif flow_type == FlowTypeEnum.AUTOSCHED:
            return AutoSchedFlow(config)
        elif flow_type == FlowTypeEnum.CONDITIONAL:
            raise NotImplementedError("Conditional flow is not implemented yet")
        elif flow_type == FlowTypeEnum.SEQUENTIALLOOP:
            return SequentialLoopFlow(config)
        elif flow_type == FlowTypeEnum.AUTOSCHEDLOOP:
            return AutoSchedLoopFlow(config)
        else:
            raise ValueError(f"Unknown flow type: {flow_type}")


