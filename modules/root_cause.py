
import pandas as pd
import numpy as np


# --------------------------------------------------
# 1. AGGREGATE RECURRING CUSTOMER COMPLAINTS
# --------------------------------------------------

def aggregate_complaints(reviews):

    df = reviews.copy()

    # Consider Negative and Mixed reviews as potential
    # complaint-bearing reviews.
    complaints = df[
        df["sentiment"].isin(["Negative", "Mixed"])
    ].copy()

    if complaints.empty:
        return pd.DataFrame(
            columns=["aspect", "total_complaints",
                     "affected_branches"]
        )

    result = (
        complaints.groupby("aspect")
        .agg(
            total_complaints=("review_id", "count"),
            affected_branches=("branch", "nunique")
        )
        .reset_index()
        .sort_values(
            "total_complaints",
            ascending=False
        )
    )

    return result


# --------------------------------------------------
# 2. ANALYZE COMPLAINT PATTERNS BY BRANCH
# --------------------------------------------------

def analyze_branch_patterns(reviews):

    df = reviews.copy()

    df["is_complaint"] = df["sentiment"].isin(
        ["Negative", "Mixed"]
    )

    result = (
        df.groupby("branch")
        .agg(
            total_reviews=("review_id", "count"),
            complaint_count=("is_complaint", "sum"),
            average_rating=("rating", "mean")
        )
        .reset_index()
    )

    result["complaint_percentage"] = (
        result["complaint_count"] /
        result["total_reviews"] * 100
    ).round(2)

    result["average_rating"] = (
        result["average_rating"].round(2)
    )

    return result.sort_values(
        "complaint_percentage",
        ascending=False
    )


# --------------------------------------------------
# 3. COMPARE REVIEWS WITH OPERATIONAL METRICS
# --------------------------------------------------

def compare_operational_metrics(reviews, operations):

    review_data = reviews.copy()
    ops_data = operations.copy()

    review_data["review_date"] = pd.to_datetime(
        review_data["review_date"],
        errors="coerce"
    )

    ops_data["date"] = pd.to_datetime(
        ops_data["date"],
        errors="coerce"
    )

    review_data = review_data.dropna(
        subset=["review_date"]
    )

    ops_data = ops_data.dropna(subset=["date"])

    # Aggregate by branch and week to avoid relying
    # on individual days with very few reviews.

    review_data["week_start"] = (
        review_data["review_date"]
        .dt.to_period("W")
        .dt.start_time
    )

    ops_data["week_start"] = (
        ops_data["date"]
        .dt.to_period("W")
        .dt.start_time
    )

    review_data["is_complaint"] = (
        review_data["sentiment"].isin(
            ["Negative", "Mixed"]
        )
    )

    review_stats = (
        review_data.groupby(["branch", "week_start"])
        .agg(
            total_reviews=("review_id", "count"),
            complaint_count=("is_complaint", "sum")
        )
        .reset_index()
    )

    review_stats["complaint_percentage"] = (
        review_stats["complaint_count"] /
        review_stats["total_reviews"] * 100
    ).round(2)

    # Aggregate operational information weekly.

    ops_stats = (
        ops_data.groupby(["branch", "week_start"])
        .agg(
            total_orders=("orders_count", "sum"),
            average_staff=("staff_count", "mean"),
            average_prep_time=(
                "avg_order_prep_time_minutes", "mean"
            ),
            total_refunds=("refunds_count", "sum")
        )
        .reset_index()
    )

    ops_stats["staff_per_100_orders"] = (
        ops_stats["average_staff"] /
        ops_stats["total_orders"] * 100
    )

    ops_stats["refund_rate"] = (
        ops_stats["total_refunds"] /
        ops_stats["total_orders"] * 100
    )

    # Combine both datasets.

    comparison = pd.merge(
        review_stats,
        ops_stats,
        on=["branch", "week_start"],
        how="left"
    )

    return comparison


# --------------------------------------------------
# 4. IDENTIFY UNUSUAL OPERATIONAL RISK FACTORS
# --------------------------------------------------

def identify_risk_factors(comparison):

    df = comparison.copy()

    if df.empty:
        return df

    # Use relative thresholds derived from the
    # available operational dataset.

    valid_prep = df["average_prep_time"].dropna()
    valid_staff = df["staff_per_100_orders"].dropna()
    valid_refunds = df["refund_rate"].dropna()

    if valid_prep.empty:
        return df

    prep_threshold = valid_prep.quantile(0.75)

    staff_threshold = (
        valid_staff.quantile(0.25)
        if not valid_staff.empty else None
    )

    refund_threshold = (
        valid_refunds.quantile(0.75)
        if not valid_refunds.empty else None
    )

    def detect_risks(row):

        risks = []

        if (
            pd.notna(row["average_prep_time"])
            and row["average_prep_time"] > prep_threshold
        ):
            risks.append(
                "Higher-than-usual order preparation time"
            )

        if (
            staff_threshold is not None
            and pd.notna(row["staff_per_100_orders"])
            and row["staff_per_100_orders"] < staff_threshold
        ):
            risks.append(
                "Lower staffing relative to order volume"
            )

        if (
            refund_threshold is not None
            and pd.notna(row["refund_rate"])
            and row["refund_rate"] > refund_threshold
        ):
            risks.append(
                "Higher-than-usual refund rate"
            )

        return risks

    df["risk_factors"] = df.apply(
        detect_risks,
        axis=1
    )

    df["risk_factor_count"] = (
        df["risk_factors"].apply(len)
    )

    # Mark complaint patterns that have enough
    # observations for a more meaningful comparison.

    df["sufficient_review_data"] = (
        df["total_reviews"] >= 3
    )

    df["investigation_priority"] = "Low"

    df.loc[
        (df["risk_factor_count"] >= 2) &
        (df["complaint_count"] > 0) &
        df["sufficient_review_data"],
        "investigation_priority"
    ] = "High"

    df.loc[
        (df["risk_factor_count"] >= 1) &
        (df["complaint_count"] > 0) &
        df["sufficient_review_data"] &
        (df["risk_factor_count"] < 2),
        "investigation_priority"
    ] = "Medium"

    return df


# --------------------------------------------------
# 5. GENERATE ROOT CAUSE INVESTIGATION REPORT
# --------------------------------------------------

def generate_root_cause_report(reviews, operations):

    complaints = aggregate_complaints(reviews)

    branches = analyze_branch_patterns(reviews)

    comparison = compare_operational_metrics(
        reviews,
        operations
    )

    risk_analysis = identify_risk_factors(
        comparison
    )

    findings = []

    for _, row in risk_analysis.iterrows():

        if row["complaint_count"] == 0:
            continue

        if row["risk_factor_count"] == 0:
            continue

        findings.append({
            "branch": row["branch"],
            "week_start": row["week_start"],
            "complaints": int(row["complaint_count"]),
            "total_reviews": int(row["total_reviews"]),
            "complaint_percentage": float(
                row["complaint_percentage"]
            ),
            "possible_risk_factors": row["risk_factors"],
            "average_prep_time": row["average_prep_time"],
            "staff_per_100_orders": row[
                "staff_per_100_orders"
            ],
            "refund_rate": row["refund_rate"],
            "priority": row["investigation_priority"],
            "evidence_status": (
                "Needs further investigation"
            )
        })

    # Correlation is descriptive, not proof of causation.
    correlation_columns = [
        "complaint_percentage",
        "average_prep_time",
        "staff_per_100_orders",
        "refund_rate"
    ]

    correlation_data = risk_analysis[
        correlation_columns
    ].dropna()

    correlations = {}

    if len(correlation_data) >= 5:

        corr = correlation_data.corr()

        correlations = (
            corr["complaint_percentage"]
            .drop("complaint_percentage")
            .to_dict()
        )

    return {
        "complaints": complaints,
        "branches": branches,
        "operational_comparison": comparison,
        "risk_analysis": risk_analysis,
        "findings": findings,
        "correlations": correlations
    }
