from dataclasses import dataclass

from agents.config import WorkflowConfig
from agents.jira import JiraClient
from agents.knowledge import KnowledgeBase
from agents.model import PlanningModel
from agents.repository import DemoRepository
from agents.store import JobStore


@dataclass
class WorkflowServices:
    config: WorkflowConfig
    store: JobStore
    repository: DemoRepository
    model: PlanningModel
    knowledge_base: KnowledgeBase | None = None
    jira_client: JiraClient | None = None
