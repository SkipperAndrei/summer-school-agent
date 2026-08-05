"""
Tools available to the Summer School AI Assistant.

The tools currently access a local Markdown knowledge base.
Later, the same operations will use Google Cloud Storage.
"""

import csv
import io
from typing import Dict, List, Optional

from app.knowledge import KnowledgeProvider

_CACHED_EXERCISES: Optional[List[Dict[str, str]]] = None

class AssistantTools:
    """Operations that the AI agent can perform on the knowledge base."""

    def __init__(self, knowledge_provider: KnowledgeProvider):
        self.knowledge = knowledge_provider

    def list_documents(self) -> dict:
        """
        List the available knowledge documents.

        Use this tool when the user asks what information, topics,
        files, or workshop materials are available.

        Returns:
            A dictionary containing the operation status and filenames.
        """
        documents = self.knowledge.list_documents()

        return {
            "status": "success",
            "documents": documents,
            "document_count": len(documents),
        }

    def read_document(self, filename: str) -> dict:
        """
        Read a specific document from the knowledge base.

        Use this tool when the user asks about the contents of a known
        document or when another tool identifies a relevant filename.

        Args:
            filename: Exact Markdown filename, such as "day2.md".

        Returns:
            A dictionary containing the document content or an error.
        """
        try:
            content = self.knowledge.read_document(filename)
        except FileNotFoundError:
            return {
                "status": "error",
                "filename": filename,
                "error_message": f"Document '{filename}' was not found.",
            }

        return {
            "status": "success",
            "filename": filename,
            "content": content,
        }

    def search_documents(self, keyword: str) -> dict:
        """
        Search all knowledge documents and return short matching excerpts.

        Use this tool when the user asks which workshop materials mention
        a particular concept, service, command, or technology.

        Args:
            keyword: Word or phrase to search for, such as "Docker".

        Returns:
            A dictionary containing matching filenames and line excerpts.
        """
        normalized_keyword = keyword.strip().casefold()

        if not normalized_keyword:
            return {
                "status": "error",
                "keyword": keyword,
                "error_message": "The search keyword cannot be empty.",
            }

        matches: list[dict] = []

        for filename in self.knowledge.list_documents():
            content = self.knowledge.read_document(filename)
            excerpts: list[dict] = []

            for line_number, line in enumerate(content.splitlines(), start=1):
                if normalized_keyword in line.casefold():
                    excerpts.append(
                        {
                            "line_number": line_number,
                            "text": line.strip(),
                        }
                    )

                if len(excerpts) == 3:
                    break

            if excerpts:
                matches.append(
                    {
                        "filename": filename,
                        "excerpts": excerpts,
                    }
                )

        return {
            "status": "success",
            "keyword": keyword,
            "matches": matches,
            "match_count": len(matches),
        }

    def filter_results(self, target_muscle: Optional[str] = None, 
                       level: Optional[str] = None, 
                       equipment: Optional[List[str]] = None, 
                       type: Optional[str] = None,
                       max_matches: int = 8) -> dict:
        """
        Filter exercises from the knowledge base based on specified criteria.
        This tool should be used when the user asks for alternatives or specific exercises based on available equipment, target muscle, level, or type.

        Args:
            target_muscle: The muscle group to target (e.g., "chest", "legs").
            level: The difficulty level of the exercise (e.g., "beginner", "intermediate", "advanced").
            equipment: A list of available equipment (e.g., ["dumbbell", "kettlebells"]).
            type: The type of exercise (e.g., "strength", "powerlifting").
            max_matches: Maximum number of exercises to return.

        Returns:
            A dictionary containing the filtered exercises or an error message.
        """
        global _CACHED_EXERCISES

        if _CACHED_EXERCISES is None:
            try:
                raw_md_content = self.read_document("exercises.md")
                
                clean_csv_str = raw_md_content.get("content").strip()
                if clean_csv_str.startswith("```"):
                    lines = clean_csv_str.splitlines()
                    clean_csv_str = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

                csv_file = io.StringIO(clean_csv_str.strip())
                reader = csv.DictReader(csv_file)
                
                parsed_rows = []
                for row in reader:
                    normalized_row = {
                        k.strip().lower().replace(" ", "_"): v.strip() 
                        for k, v in row.items() if k
                    }
                    parsed_rows.append(normalized_row)
                    
                _CACHED_EXERCISES = parsed_rows
                
            except Exception as e:
                return {
                        "status": "error", 
                        "message": f"Failed to parse exercises.md: {str(e)}"
                }

        exercises = _CACHED_EXERCISES
        matches = []

        target_muscle = target_muscle.strip().lower() if target_muscle else None
        level = level.strip().lower() if level else None
        equipment = [e.strip().lower() for e in equipment] if equipment else None
        type = type.strip().lower() if type else None

        for ex in exercises:
            if target_muscle and ex.get("bodypart") != target_muscle:
                continue
            if level and ex.get("level") != level:
                continue
            if equipment and ex.get("equipment") not in equipment:
                continue
            if type and ex.get("type") != type:
                continue

            matches.append(ex)

            if len(matches) >= max_matches:
                break

        if not matches:
            return {
                "status": "success",
                "message": "No exercises found matching the criteria.",
                "matches": [],
            }

        return {
            "status": "success",
            "message": "Here are some exercises matching the criteria",
            "nr_matches": len(matches),
            "matches": matches
        }