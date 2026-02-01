"""PRD (Product Requirements Document) data models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PRDMetadata(BaseModel):
    """Metadata for a PRD document."""

    title: str = Field(..., description="PRD title")
    version: str = Field(default="1.0", description="Document version")
    author: str | None = Field(default=None, description="Document author")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    tags: list[str] = Field(default_factory=list, description="Document tags")
    description: str | None = Field(default=None, description="Brief description")


class PRDSection(BaseModel):
    """A section within a PRD document."""

    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")
    level: int = Field(default=1, ge=1, le=6, description="Heading level (1-6)")
    subsections: list["PRDSection"] = Field(
        default_factory=list, description="Nested subsections"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def get_all_content(self) -> str:
        """Get all content including subsections recursively."""
        parts = [self.content]
        for subsection in self.subsections:
            parts.append(subsection.get_all_content())
        return "\n\n".join(parts)


class PRD(BaseModel):
    """Complete PRD document."""

    metadata: PRDMetadata = Field(..., description="Document metadata")
    sections: list[PRDSection] = Field(..., description="Document sections")
    raw_content: str | None = Field(default=None, description="Original raw content")

    def get_full_text(self) -> str:
        """Get full document text including all sections."""
        parts = []
        for section in self.sections:
            parts.append(f"# {section.title}")
            parts.append(section.get_all_content())
        return "\n\n".join(parts)

    def get_summary(self) -> str:
        """Get a brief summary of the PRD."""
        summary_parts = [
            f"Title: {self.metadata.title}",
            f"Version: {self.metadata.version}",
            f"Sections: {len(self.sections)}",
        ]
        if self.metadata.description:
            summary_parts.append(f"Description: {self.metadata.description}")
        return "\n".join(summary_parts)
