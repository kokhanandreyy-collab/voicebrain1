import httpx

class ReadwiseService:
    def __init__(self):
        self.api_url = "https://readwise.io/api/v3"

    async def save_to_reader(self, access_token: str, note_data: dict) -> bool:
        """
        Saves a note to Readwise Reader.
        note_data should contain: title, url (optional), html/text, tags, author
        """
        if not access_token or access_token.startswith("mock_"):
            print(f"[Mock Readwise] Would save document: {note_data.get('title')}")
            return True

        payload = {
            "url": note_data.get("url", "https://voicebrain.app/notes/placeholder"),
            "title": note_data.get("title", "Voice Note"),
            "html": note_data.get("html", ""),  # Reader prefers HTML content
            "author": note_data.get("author", "VoiceBrain"),
            "tags": note_data.get("tags", []),
            "should_clean_html": True
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_url}/save",
                    json=payload,
                    headers={"Authorization": f"Token {access_token}"}
                )
                if response.status_code in [200, 201]:
                    return True
                else:
                    print(f"[Readwise Error] {response.status_code}: {response.text}")
                    return False
            except Exception as e:
                print(f"[Readwise Exception] {e}")
                return False

readwise_service = ReadwiseService()
