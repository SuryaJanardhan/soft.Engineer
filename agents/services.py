from dataclasses import dataclass

from agents.config import WorkflowConfig
from agents.jira import JiraClient
from agents.knowledge import KnowledgeBase
from agents.model import PlanningModel
from agents.repository import DemoRepository
from agents.sdk_runtime import OpenHandsCodingRuntime
from agents.store import JobStore


from agents.notifier import NotificationService


@dataclass
class WorkflowServices:
    config: WorkflowConfig
    store: JobStore
    repository: DemoRepository
    model: PlanningModel
    knowledge_base: KnowledgeBase | None = None
    jira_client: JiraClient | None = None
    notifier: NotificationService | None = None
    sdk_runtime: OpenHandsCodingRuntime | None = None

