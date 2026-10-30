
import pandas as pd


def generate_overview(reviews):

    total_reviews = len(reviews)

    sentiment_counts = (
        reviews["sentiment"]
        .value_counts()
        .to_dict()
    )

    negative_reviews = sentiment_counts.get("Negative", 0)

    negative_percentage = (
        negative_reviews / total_reviews * 100
        if total_reviews else 0
    )

    return {
        "total_reviews": total_reviews,
        "average_rating": round(
            reviews["rating"].mean(), 2
        ),
        "negative_reviews": negative_reviews,
        "negative_percentage": round(
            negative_percentage, 2
        ),
        "sentiment_counts": sentiment_counts
    }


def get_theme_analysis(reviews):

    result = (
        reviews.groupby("theme")
        .agg(
            total_reviews=("review_id", "count"),
            average_rating=("rating", "mean"),
            negative_reviews=(
                "sentiment",
                lambda x: (x == "Negative").sum()
            )
        )
        .reset_index()
        .sort_values(
            "total_reviews",
            ascending=False
        )
    )

    result["negative_percentage"] = (
        result["negative_reviews"] /
        result["total_reviews"] * 100
    ).round(2)

    result["average_rating"] = (
        result["average_rating"].round(2)
    )

    return result


def get_branch_analysis(reviews):

    result = (
        reviews.groupby("branch")
        .agg(
            total_reviews=("review_id", "count"),
            average_rating=("rating", "mean"),
            negative_reviews=(
                "sentiment",
                lambda x: (x == "Negative").sum()
            )
        )
        .reset_index()
    )

    result["negative_percentage"] = (
        result["negative_reviews"] /
        result["total_reviews"] * 100
    ).round(2)

    result["average_rating"] = (
        result["average_rating"].round(2)
    )

    return result.sort_values(
        "negative_percentage",
        ascending=False
    )


def get_daily_trends(reviews):

    df = reviews.copy()

    df["review_date"] = pd.to_datetime(
        df["review_date"]
    )

    df["date"] = df["review_date"].dt.date

    result = (
        df.groupby("date")
        .agg(
            total_reviews=("review_id", "count"),
            negative_reviews=(
                "sentiment",
                lambda x: (x == "Negative").sum()
            ),
            average_rating=("rating", "mean")
        )
        .reset_index()
    )

    return result


def compare_operations(reviews, operations):

    review_data = reviews.copy()
    operations_data = operations.copy()

    review_data["date"] = pd.to_datetime(
        review_data["review_date"]
    ).dt.date

    operations_data["date"] = pd.to_datetime(
        operations_data["date"]
    ).dt.date

    # Calculate daily negative review statistics
    review_stats = (
        review_data.groupby(["branch", "date"])
        .agg(
            total_reviews=("review_id", "count"),
            negative_reviews=(
                "sentiment",
                lambda x: (x == "Negative").sum()
            )
        )
        .reset_index()
    )

    review_stats["negative_percentage"] = (
        review_stats["negative_reviews"] /
        review_stats["total_reviews"] * 100
    ).round(2)

    # Match reviews with operational data
    comparison = pd.merge(
        review_stats,
        operations_data,
        on=["branch", "date"],
        how="left"
    )

    return comparison


def get_all_analytics(reviews, operations=None):

    results = {
        "overview": generate_overview(reviews),
        "themes": get_theme_analysis(reviews),
        "branches": get_branch_analysis(reviews),
        "daily_trends": get_daily_trends(reviews)
    }

    if operations is not None:
        results["operations"] = compare_operations(
            reviews,
            operations
        )

    return results
