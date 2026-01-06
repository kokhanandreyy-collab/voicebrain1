from .orchestrator import PipelineOrchestrator
from .stages import PipelineStages

class NotePipelineWrapper:
    """
    Backward compatible interface for the decomposed pipeline service.
    """
    def __init__(self):
        self._orchestrator = PipelineOrchestrator()
        self.stages = PipelineStages()

    async def process(self, note_id: str):
        """Standard entry point for processing a note through all stages."""
        await self._orchestrator.run(note_id)

# Singleton instance for the project
pipeline = NotePipelineWrapper()
