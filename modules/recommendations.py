
import os
import json
import pandas as pd

from typing import Literal
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is missing in .env")

client = genai.Client(api_key=API_KEY)


# --------------------------------------------------
# 1. DEFINE RECOMMENDATION OUTPUT STRUCTURE
# --------------------------------------------------

class Recommendation(BaseModel):

    branch: str

    problem: str

    evidence_summary: str

    possible_explanations: list[str]

    recommended_actions: list[str]

    priority: Literal["High", "Medium", "Low"]

    success_metrics: list[str]

    validation_needed: str


class RecommendationBatch(BaseModel):
    recommendations: list[Recommendation]


# --------------------------------------------------
# 2. PREPARE FINDING CONTEXT
# --------------------------------------------------

def prepare_finding_context(root_cause_report, reviews):

    findings = root_cause_report["findings"]

    contexts = []

    for finding in findings:

        branch = finding["branch"]
        week_start = pd.to_datetime(
            finding["week_start"]
        )

        week_end = week_start + pd.Timedelta(days=6)

        # Find reviews belonging to the same branch
        # and investigation week.

        branch_reviews = reviews[
            (reviews["branch"] == branch) &
            (reviews["review_date"] >= week_start) &
            (reviews["review_date"] < week_end + pd.Timedelta(days=1)) &
            (reviews["sentiment"].isin(["Negative", "Mixed"]))
        ]

        review_examples = []

        for _, review in branch_reviews.head(5).iterrows():

            review_examples.append({
                "review_id": str(review["review_id"]),
                "review_text": str(review["review_text"]),
                "aspect": str(review["aspect"]),
                "sentiment": str(review["sentiment"])
            })

        context = {
            "branch": branch,
            "week_start": str(week_start.date()),
            "complaints": finding["complaints"],
            "total_reviews": finding["total_reviews"],
            "complaint_percentage": finding[
                "complaint_percentage"
            ],
            "operational_risk_factors": finding[
                "possible_risk_factors"
            ],
            "average_prep_time": finding[
                "average_prep_time"
            ],
            "staff_per_100_orders": finding[
                "staff_per_100_orders"
            ],
            "refund_rate": finding["refund_rate"],
            "review_examples": review_examples
        }

        contexts.append(context)

    return contexts


# --------------------------------------------------
# 3. CREATE AI PROMPT
# --------------------------------------------------

def create_recommendation_prompt(contexts):

    prompt = f"""
You are an experienced restaurant operations consultant.

Your task is to convert customer feedback and
operational observations into practical recommendations.

Analyze the following investigation findings:

{json.dumps(contexts, indent=2, default=str)}

IMPORTANT RULES:

1. Only use the evidence supplied.
2. Never claim that a possible risk factor is
   a confirmed root cause.
3. Clearly distinguish observations from hypotheses.
4. Do not invent customer reviews, metrics or events.
5. Recommend practical actions that a restaurant
   manager can implement.
6. Each recommendation must contain measurable
   success metrics.
7. If evidence is insufficient, explicitly state
   that further investigation is needed.
8. Use the provided branch name.
9. Prioritize actions according to the available
   evidence and potential business impact.
10. Do not recommend expensive interventions
    without sufficient supporting evidence.

For every finding, generate:

- Branch
- Problem
- Evidence summary
- Possible explanations
- Recommended actions
- Priority
- Success metrics
- Validation needed

Return one recommendation for each supplied finding.
"""

    return prompt


# --------------------------------------------------
# 4. VALIDATE AI RECOMMENDATIONS
# --------------------------------------------------

def validate_recommendations(result, contexts):

    valid_branches = {
        context["branch"] for context in contexts
    }

    for recommendation in result.recommendations:

        if recommendation.branch not in valid_branches:
            raise ValueError(
                f"Unknown branch: {recommendation.branch}"
            )

        if not recommendation.recommended_actions:
            raise ValueError(
                "Recommendation contains no actions"
            )

        if not recommendation.success_metrics:
            raise ValueError(
                "Recommendation contains no success metrics"
            )

        if not recommendation.evidence_summary.strip():
            raise ValueError(
                "Evidence summary cannot be empty"
            )

    return result


# --------------------------------------------------
# 5. GENERATE RECOMMENDATIONS USING GEMINI
# --------------------------------------------------

def generate_recommendations(root_cause_report, reviews):

    contexts = prepare_finding_context(
        root_cause_report,
        reviews
    )

    if not contexts:
        return []

    prompt = create_recommendation_prompt(contexts)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": RecommendationBatch,
            "temperature": 0.2
        }
    )

    if response.parsed is not None:
        result = response.parsed
    else:
        result = RecommendationBatch.model_validate_json(
            response.text
        )

    result = validate_recommendations(
        result,
        contexts
    )

    return [
        item.model_dump()
        for item in result.recommendations
    ]


# --------------------------------------------------
# 6. SAVE RECOMMENDATIONS
# --------------------------------------------------

def save_recommendations(recommendations, filepath):

    if not recommendations:
        print("No recommendations available.")
        return

    df = pd.DataFrame(recommendations)

    # Convert lists into readable strings for CSV.

    for column in [
        "possible_explanations",
        "recommended_actions",
        "success_metrics"
    ]:
        df[column] = df[column].apply(
            lambda values: " | ".join(values)
        )

    os.makedirs(
        os.path.dirname(filepath) or ".",
        exist_ok=True
    )

    df.to_csv(filepath, index=False)

    print(
        f"Recommendations saved to {filepath}"
    )
