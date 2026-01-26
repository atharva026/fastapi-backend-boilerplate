from typing import Dict, Optional

class ResponseBuilder:
    """
    Builds FastAPI OpenAPI `responses` entries with multiple examples.
    """

    @staticmethod
    def build(
        status_code: int,
        *example_dicts: Dict[str, Dict],
        description: Optional[str] = None,
    ) -> Dict[int, Dict]:
        """
        Build a FastAPI response entry with multiple examples.

        Args:
            status_code: HTTP status code (e.g., 401, 403)
            *example_dicts: One or more example dictionaries
            description: Optional custom description

        Returns:
            Dict suitable for FastAPI `responses` parameter
        """
        merged_examples: Dict[str, Dict] = {}

        for ex in example_dicts:
            merged_examples.update(ex)

        return {
            status_code: {
                "description": description
                or " / ".join(example["summary"] for example in merged_examples.values()),
                "content": {
                    "application/json": {
                        "examples": merged_examples
                    }
                },
            }
        }
