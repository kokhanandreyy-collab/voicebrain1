from .base import BaseIntegration
from app.models import Integration, Note
import httpx
import logging

class LinearIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to Linear")
        
        token = integration.access_token
        team_id = (integration.settings or {}).get("team_id")
        
        if not team_id:
             self.logger.warning("No Team ID configured for Linear integration.")
             raise ValueError("Linear Team ID not configured. Please select a team in settings.")

        if not note.action_items:
            self.logger.info("No action items to sync to Linear.")
            return

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = "https://api.linear.app/graphql"

        mutation = """
        mutation IssueCreate($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    title
                    url
                }
            }
        }
        """

        async with httpx.AsyncClient() as client:
            for item in note.action_items:
                # Description includes summary + link to VoiceBrain source
                description = f"{note.summary or 'No summary provided.'}\n\n---\nExtracted from VoiceBrain Note: https://voicebrain.app/notes/{note.id}"
                
                variables = {
                        "input": {
                        "teamId": team_id,
                        "title": str(item)[:250],
                        "description": description
                    }
                }

                try:
                    response = await client.post(
                        url, 
                        headers=headers, 
                        json={"query": mutation, "variables": variables}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "errors" in data:
                             self.logger.error(f"Linear GraphQL Error: {data['errors']}")
                             # Consider raising if critical, but for multi-item, maybe logging is safer?
                             # Let's count it as error for the log.
                        else:
                             issue = data.get("data", {}).get("issueCreate", {}).get("issue", {})
                             self.logger.info(f"Created Linear Issue: {issue.get('title')} ({issue.get('url')})")
                    else:
                        self.logger.error(f"Linear API Error ({response.status_code}): {response.text}")
                        
                except Exception as e:
                    self.logger.error(f"Failed to create Linear issue for '{item}': {e}")
                    raise e
