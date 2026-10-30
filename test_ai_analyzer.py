from modules.preprocessing import load_reviews
from modules.ai_analyzer import analyze_reviews

# Load cleaned reviews
reviews = load_reviews(
    "data/raw/sample_reviews.csv"
)

# Analyze only 5 reviews initially
analyzed = analyze_reviews(
    reviews,
    batch_size=5,
    max_reviews=5
)

# Display results
print("\nAI ANALYSIS RESULTS:\n")

print(
    analyzed[
        [
            "review_id",
            "sentiment",
            "aspect",
            "theme",
            "severity",
            "confidence"
        ]
    ].to_string(index=False)
)

# Save results
analyzed.to_csv(
    "data/processed/analyzed_reviews.csv",
    index=False
)

print("\nAnalysis saved successfully!")