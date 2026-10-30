
from modules.preprocessing import (
    load_reviews,
    load_operations
)

from modules.ai_analyzer import analyze_reviews

from modules.analytics import get_all_analytics


# Load datasets
reviews = load_reviews(
    "data/raw/sample_reviews.csv"
)

operations = load_operations(
    "data/raw/sample_operations.csv"
)

# Load existing AI results if available
import os
import pandas as pd

processed_path = "data/processed/analyzed_reviews.csv"

if os.path.exists(processed_path):
    analyzed_reviews = pd.read_csv(processed_path)
else:
    analyzed_reviews = analyze_reviews(
        reviews,
        batch_size=5
    )

analyzed_reviews["review_date"] = pd.to_datetime(
    analyzed_reviews["review_date"]
)

# Generate analytics
results = get_all_analytics(
    analyzed_reviews,
    operations
)

print("\n===== OVERVIEW =====")
print(results["overview"])

print("\n===== THEME ANALYSIS =====")
print(results["themes"].to_string(index=False))

print("\n===== BRANCH ANALYSIS =====")
print(results["branches"].to_string(index=False))

print("\n===== OPERATIONAL COMPARISON =====")
print(results["operations"].head(10).to_string(index=False))

# Save processed analytics
results["themes"].to_csv(
    "outputs/theme_analysis.csv",
    index=False
)

results["branches"].to_csv(
    "outputs/branch_analysis.csv",
    index=False
)

results["operations"].to_csv(
    "outputs/operational_comparison.csv",
    index=False
)

print("\nAnalytics generated successfully!")
