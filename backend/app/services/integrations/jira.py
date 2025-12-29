from .base import BaseIntegration
from app.models import Integration, Note
import httpx
import logging
import json

class JiraIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to Jira")
        
        token = integration.auth_token
        # Jira projects are identified by key (e.g. PROJ)
        project_key = (integration.settings or {}).get("project_key")
        
        if not project_key:
             self.logger.warning("No Project Key configured for Jira integration.")
             raise ValueError("Jira Project Key not configured. Please enter a Project Key in settings.")

        if not note.action_items:
            self.logger.info("No action items to sync to Jira.")
            return

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient() as client:
            settings = integration.settings or {}
            custom_domain = settings.get("custom_domain")
            is_pat = settings.get("is_pat") or (token and not token.startswith("ey")) # Simple heuristic, or explicit flag
            
            api_url = ""
            
            # Logic Branch: Cloud vs On-Prem/PAT
            if custom_domain or is_pat:
                domain = custom_domain or "jira.atlassian.com" # Fallback if PAT used without domain (unlikely but safe)
                if not domain.startswith("http"):
                    domain = f"https://{domain}"
                
                # On-Prem / PAT often uses V2 or just standard /rest/api/2/issue
                # V3 is Cloud specific usually, V2 is safer for on-prem.
                api_url = f"{domain}/rest/api/2/issue"
                self.logger.debug(f"Using Custom Jira Domain: {domain}")
            else:
                # Cloud OAuth Flow
                try:
                    # 1. Discover Cloud ID
                    resource_resp = await client.get("https://api.atlassian.com/oauth/token/accessible-resources", headers=headers)
                    if resource_resp.status_code == 401:
                         self.logger.error("Jira OAuth Unauthorized. Token might be expired.")
                         raise Exception("Unauthorized. Please reconnect Jira.")
                    
                    if resource_resp.status_code != 200:
                        raise Exception(f"Failed to fetch Jira resources: {resource_resp.text}")
                    
                    resources = resource_resp.json()
                    if not resources:
                        raise Exception("No Jira resources (sites) found for this user.")
                    
                    cloud_id = resources[0]['id']
                    self.logger.debug(f"Using Jira Cloud ID: {cloud_id}")
                    api_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue"
                    
                except Exception as e:
                    self.logger.error(f"Jira Connection Failed: {e}")
                    raise e
            
            # 2. Create Issues
            for item in note.action_items:
                # Construct Payload
                description_content = f"Context: {note.summary or 'No summary'}\n\nView Full Note: https://voicebrain.app/notes/{note.id}"
                
                payload = {
                     "fields": {
                        "project": { "key": project_key },
                        "summary": str(item),
                        "issuetype": { "name": "Task" },
                        "labels": ["VoiceBrain"]
                    }
                }
                
                # ADF vs String Description
                # Cloud (V3) needs ADF. On-Prem (V2) often takes string description.
                if "api/3/" in api_url:
                     payload["fields"]["description"] = {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{ "type": "text", "text": description_content }]
                            }
                        ]
                    }
                else:
                    # V2 / On-Prem
                    payload["fields"]["description"] = description_content

                try:
                    response = await client.post(api_url, headers=headers, json=payload)
                    
                    if response.status_code in (201, 200):
                        data = response.json()
                        self.logger.info(f"Created Jira Issue: {data.get('key')}")
                    elif response.status_code == 404:
                         self.logger.error(f"Jira 404 Error. Check Project Key '{project_key}' and Domain URL.")
                    elif response.status_code == 401:
                         self.logger.error("Jira 401 Unauthorized. Check Access Token or PAT.")
                    else:
                        self.logger.error(f"Jira API Error ({response.status_code}): {response.text}")
                        
                except Exception as e:
                    self.logger.error(f"Failed to create Jira issue for '{item}': {e}")
