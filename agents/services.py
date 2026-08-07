from dataclasses import dataclass

from agents.config import WorkflowConfig
from agents.model import PlanningModel
from agents.repository import DemoRepository
from agents.store import JobStore


@dataclass
class WorkflowServices:
    config: WorkflowConfig
    store: JobStore
    repository: DemoRepository
    model: PlanningModel
