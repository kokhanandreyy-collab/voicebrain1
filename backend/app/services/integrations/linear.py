from typing import List, Optional, Dict, Any
from .base import BaseIntegration
from app.models import Integration, Note
import httpx

class LinearIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note) -> None:
        self.logger.info(f"Syncing note {note.id} to Linear")
        
        token: Optional[str] = integration.auth_token
        team_id: Optional[str] = (integration.settings or {}).get("team_id")
        
        if not team_id:
             self.logger.warning("No Team ID configured for Linear integration.")
             raise ValueError("Linear Team ID not configured. Please select a team in settings.")

        if not note.action_items:
            self.logger.info("No action items to sync to Linear.")
            return

        headers: Dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url: str = "https://api.linear.app/graphql"

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

        for item in (note.action_items or []):
            # Description includes summary + link to VoiceBrain source
            description: str = f"{note.summary or 'No summary provided.'}\n\n---\nExtracted from VoiceBrain Note: https://voicebrain.app/notes/{note.id}"
            
            variables: Dict[str, Any] = {
                    "input": {
                    "teamId": team_id,
                    "title": str(item)[:250],
                    "description": description
                }
            }

            try:
                response: httpx.Response = await self.request(
                    "POST",
                    url, 
                    headers=headers, 
                    json={"query": mutation, "variables": variables}
                )
                
                response.raise_for_status()
                data: Dict[str, Any] = response.json()
                
                if "errors" in data:
                     self.logger.error(f"Linear GraphQL Error: {data['errors']}")
                else:
                     issue: Dict[str, Any] = data.get("data", {}).get("issueCreate", {}).get("issue", {})
                     self.logger.info(f"Created Linear Issue: {issue.get('title')} ({issue.get('url')})")
                        
            except httpx.HTTPStatusError as e:
                self.logger.error(f"Linear API Status Error ({e.response.status_code}): {e.response.text}")
                raise
            except httpx.RequestError as e:
                self.logger.error(f"Linear API Request Error: {e}")
                raise
            except Exception as e:
                self.logger.error(f"Failed to create Linear issue for '{item}': {e}")
                raise
