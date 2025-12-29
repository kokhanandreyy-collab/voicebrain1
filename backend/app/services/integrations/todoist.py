import difflib
from .base import BaseIntegration
from app.models import Integration, Note
from app.services.todoist_service import todoist_service

class TodoistIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        # 1. Config Check
        settings = integration.settings or {}
        auto_sync = settings.get("auto_sync", True)
        
        if not auto_sync:
            self.logger.info("Auto-sync disabled for Todoist")
            return

        if not note.action_items:
            self.logger.info("No action items to sync for Todoist")
            return

        # 2. Extract AI metadata
        analysis = note.ai_analysis or {}
        suggested_project_name = analysis.get("suggested_project")
        raw_priority = analysis.get("priority", 4) # Default to 4 (Low)
        
        # Priority Mapping: VoiceBrain (1 High, 4 Low) -> Todoist (4 High, 1 Low)
        # 5 - 1 = 4 (Urgent/High)
        # 5 - 4 = 1 (Normal/Low)
        todoist_priority = 5 - max(1, min(4, raw_priority))

        # 3. Smart Project Mapping
        project_id = None
        explicit_folder = analysis.get("explicit_folder")
        project_name_to_match = explicit_folder or suggested_project_name
        
        if project_name_to_match:
            projects = await todoist_service.get_projects(integration.auth_token, note.user_id)
            if projects:
                # Fuzzy Matching
                project_names = [p["name"] for p in projects]
                matches = difflib.get_close_matches(project_name_to_match, project_names, n=1, cutoff=0.6)
                
                if matches:
                    best_match = matches[0]
                    project_id = next((p["id"] for p in projects if p["name"] == best_match), None)
                    self.logger.info(f"Fuzzy matched project '{project_name_to_match}' to Todoist '{best_match}' ({project_id})")
                else:
                    self.logger.info(f"No fuzzy match for project '{project_name_to_match}', defaulting to Inbox.")

        # 4. Sync
        self.logger.info(f"Syncing {len(note.action_items)} items to Todoist for user {note.user_id} (Project: {project_id}, Priority: {todoist_priority})")
        await todoist_service.sync_tasks_to_todoist(
            integration.auth_token, 
            note.action_items, 
            project_id=project_id, 
            priority=todoist_priority
        )
