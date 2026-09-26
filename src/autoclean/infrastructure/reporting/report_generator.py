"""ReportGenerator: renders the executive report (Phase 1, FR-11) as
Markdown via Jinja2, from real, already-computed data only -- no LLM
involvement in report generation itself (the explanation text it embeds was
already generated, with its own consistency check, back in Phase 7).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Template

logger = logging.getLogger(__name__)

_REPORT_TEMPLATE = Template(
    """# AutoClean AI+ Executive Report

**Experiment ID:** {{ experiment_id }}
**Dataset:** {{ dataset_name }}
**Generated:** {{ generated_at }}

## Summary

{{ validation.notes }}

## Dataset Profile

| Metric | Before | After |
|---|---|---|
| Row count | {{ original_profile.row_count }} | {{ cleaned_profile.row_count }} |
| Missing value % | {{ "%.2f"|format(original_profile.missing_value_pct) }} | {{ "%.2f"|format(cleaned_profile.missing_value_pct) }} |
| Duplicate rows | {{ original_profile.duplicate_row_count }} | {{ cleaned_profile.duplicate_row_count }} |
| Outliers | {{ original_profile.outlier_count }} | {{ cleaned_profile.outlier_count }} |

## Approved Strategy: {{ strategy.name }}

{{ strategy.description }}

**Steps applied:**
{% for step in strategy.steps -%}
- {{ step.operation.value }}{% if step.target_column %} on column `{{ step.target_column }}`{% endif %}
{% endfor %}

## Scores

| Objective | Score |
|---|---|
| Data quality | {{ "%.2f"|format(score.data_quality_score) }} |
| Computational cost | {{ "%.2f"|format(score.computational_cost_score) }} |
| Information preservation | {{ "%.2f"|format(score.information_preservation_score) }} |
| Statistical validity | {{ "%.2f"|format(score.statistical_validity_score) }} |
| Fairness impact | {{ "%.2f"|format(score.fairness_impact_score) }} |
| Downstream ML performance | {{ "%.2f"|format(score.downstream_ml_score) }} |
| EM confidence | {{ "%.2f"|format(score.em_confidence) }} |

{% if alternatives %}
## Alternatives Considered

{% for alt in alternatives -%}
- **{{ alt.name }}** -- data quality {{ "%.2f"|format(alt.score.data_quality_score) }}, cost {{ "%.2f"|format(alt.score.computational_cost_score) }}
{% endfor %}
{% endif %}

## Explanation

{{ explanation_text }}
{% if consistency_warnings %}

**⚠ Consistency warnings raised at generation time:**
{% for warning in consistency_warnings -%}
- {{ warning }}
{% endfor %}
{% endif %}

## Decision

Approved by **{{ decided_by }}** at {{ decided_at }}.

## Validation

- Schema consistent: {{ validation.schema_consistent }}
- Quality threshold met: {{ validation.quality_threshold_met }} (score {{ "%.2f"|format(validation.quality_score) }} vs. threshold {{ "%.2f"|format(validation.quality_threshold) }})
- Remaining issues after cleaning: {{ validation.remaining_issue_count }}

---
*This report was generated automatically from computed values. The narrative in the Explanation section was reviewed by an automated consistency check against the scores above (see Phase 7).*
"""
)


class ReportGenerator:
    """Renders and writes the executive report to disk."""

    def generate(self, context: dict[str, Any], output_path: str) -> str:
        report_text = _REPORT_TEMPLATE.render(**context)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report_text, encoding="utf-8")
        logger.info("ReportGenerator wrote executive report", extra={"output_path": str(path)})
        return str(path)
