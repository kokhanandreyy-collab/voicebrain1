from .todoist import TodoistIntegration
from .readwise import ReadwiseIntegration
from .zapier import ZapierIntegration
from .notion import NotionIntegration
from .google_calendar import GoogleCalendarIntegration
from .slack import SlackIntegration
from .google_drive import GoogleDriveIntegration
from .dropbox import DropboxIntegration
from .linear import LinearIntegration
from .jira import JiraIntegration
from .clickup import ClickUpIntegration
from .email import EmailIntegration
from .markdown_export import EmailExportIntegration
from .evernote import EvernoteIntegration
from .google_fit import GoogleFitIntegration
from .microsoft_todo import MicrosoftTodoIntegration
from .ticktick import TickTickIntegration
from .reflect import ReflectIntegration
from .craft import CraftIntegration
from .yandex_disk import YandexDiskIntegration
from .weeek import WeeekIntegration
from .bitrix24 import Bitrix24Integration
from .amocrm import AmoCRMIntegration
from .kaiten import KaitenIntegration
from .vk import VKIntegration
import logging

logger = logging.getLogger(__name__)

# Registry of handlers
_registry = {
    "todoist": TodoistIntegration(),
    "readwise": ReadwiseIntegration(),
    "zapier": ZapierIntegration(),
    "notion": NotionIntegration(),
    "google_calendar": GoogleCalendarIntegration(),
    "slack": SlackIntegration(),
    "google_drive": GoogleDriveIntegration(),
    "dropbox": DropboxIntegration(),
    "linear": LinearIntegration(),
    "jira": JiraIntegration(),
    "clickup": ClickUpIntegration(),
    "email": EmailIntegration(),
    "email_backup": EmailExportIntegration(),
    "evernote": EvernoteIntegration(),
    "google_fit": GoogleFitIntegration(),
    "microsoft_todo": MicrosoftTodoIntegration(),
    "ticktick": TickTickIntegration(),
    "reflect": ReflectIntegration(),
    "craft": CraftIntegration(),
    "yandex_disk": YandexDiskIntegration(),
    "weeek": WeeekIntegration(),
    "bitrix24": Bitrix24Integration(),
    "amocrm": AmoCRMIntegration(),
    "kaiten": KaitenIntegration(),
    "vk": VKIntegration(),
}

def get_integration_handler(provider_name: str):
    return _registry.get(provider_name)

def get_supported_integrations():
    return list(_registry.keys())
