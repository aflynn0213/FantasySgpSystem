from typing import Any, Dict, Optional, Tuple

class SgpParams():
    def __init__(self, expected_categories: Dict[str, Any] = None):
        self.expected_categories = expected_categories

    def process_parameters_map(self, params_map: Dict[str, Tuple[Optional[float], Optional[float]]]):
        """
        Returns (replacement_levels, cat_stds) both dict[str, float].
        Missing numeric entries are treated as 0.0 (or you can choose another fallback).
        """
        replacement_levels: Dict[str, float] = {}
        cat_stds: Dict[str, float] = {}

        for key, (repl, std) in params_map.items():
            # normalize key (strip whitespace, uppercase)
            k = key.strip() if isinstance(key, str) else str(key)
            k = k.upper()

            # fallback to 0.0 if parsing failed
            replacement_levels[k] = float(repl) if (repl is not None) else 0.0
            cat_stds[k] = float(std) if (std is not None) else 0.0

        # Validate presence of expected categories
        if self.expected_categories:
            missing = set(self.expected_categories) - set(replacement_levels.keys())
            if missing:
                # you can raise or just warn; here we raise to make missing data explicit
                raise KeyError(f"Missing expected categories in parameters sheet: {missing}")

        self.replacement_levels = replacement_levels 
        self.cat_stds = cat_stds
