from .base import BaseIntegration
from app.models import Integration, Note
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings
import logging

class EmailIntegration(BaseIntegration):
    async def sync(self, integration: Integration, note: Note):
        self.logger.info(f"Syncing note {note.id} to Email")
        
        # We need the user's email.
        # integration.user should be loaded if lazy='joined' or if accessing triggers a load (might need async adapter if not eager)
        # In async SQLAlchemy, accessing a lazy relationship triggers an error if not loaded.
        # We'll assume the worker query fetches it or we handle it.
        # Safe fallback: if we can't access integration.user, we can't send.
        
        recipient = None
        try:
             recipient = integration.user.email
        except:
             # If relationship is not loaded or missing
             self.logger.error("User relationship not loaded for integration. Cannot send email.")
             raise Exception("User not loaded")

        if not recipient:
             raise Exception("User has no email address")

        recipients = [recipient]
        explicit_folder = (note.ai_analysis or {}).get("explicit_folder")
        if explicit_folder and "@" in explicit_folder:
            recipients.append(explicit_folder)
            self.logger.info(f"Adding explicit recipient: {explicit_folder}")

        # HTML Body
        html = f"""
        <html>
            <body>
                <h1>🎙️ {note.title or 'Untitled Note'}</h1>
                <p><strong>Date:</strong> {note.created_at.strftime('%Y-%m-%d %H:%M')}</p>
                <hr/>
                
                <h2>Summary</h2>
                <p>{note.summary or 'No summary available.'}</p>
                
                <h2>Action Items</h2>
                <ul>
        """
        if note.action_items:
            for item in note.action_items:
                html += f"<li>{item}</li>"
        else:
            html += "<li>No action items found.</li>"
            
        html += f"""
                </ul>
                <hr/>
                <h3>Transcript</h3>
                <p style="white-space: pre-wrap;">{note.transcription_text or ''}</p>
                <br/>
                <p><small>Sent via <a href="https://voicebrain.app">VoiceBrain</a></small></p>
            </body>
        </html>
        """
        
        # Configure FastMail
        # In a real app, these should be in environmental variables or core config
        # We'll rely on settings.SMTP_*
        
        conf = ConnectionConfig(
            MAIL_USERNAME=settings.SMTP_USER,
            MAIL_PASSWORD=settings.SMTP_PASSWORD,
            MAIL_FROM=settings.SMTP_FROM,
            MAIL_PORT=settings.SMTP_PORT,
            MAIL_SERVER=settings.SMTP_HOST,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )

        message = MessageSchema(
            subject=f"VoiceBrain Note: {note.title or 'Untitled'}",
            recipients=recipients,
            body=html,
            subtype=MessageType.html
        )

        fm = FastMail(conf)
        
        try:
            await fm.send_message(message)
            self.logger.info(f"Email sent to {recipient}")
        except Exception as e:
            self.logger.error(f"Email send failed: {e}")
            raise e
