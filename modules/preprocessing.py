
import pandas as pd

REVIEW_REQUIRED_COLUMNS = [
    "review_id",
    "review_text",
    "rating",
    "branch",
    "review_date",
    "platform"
]

OPERATIONS_REQUIRED_COLUMNS = [
    "branch",
    "date",
    "orders_count",
    "staff_count",
    "avg_order_prep_time_minutes",
    "refunds_count"
]


def load_reviews(file):
    df = pd.read_csv(file)
    return preprocess_reviews(df)


def load_operations(file):
    df = pd.read_csv(file)
    return preprocess_operations(df)


def preprocess_reviews(df):

    missing = set(REVIEW_REQUIRED_COLUMNS) - set(df.columns)

    if missing:
        raise ValueError(f"Missing review columns: {missing}")

    df = df.copy()

    # Remove rows without review text
    df["review_text"] = df["review_text"].fillna("").astype(str).str.strip()
    df = df[df["review_text"] != ""]

    # Remove duplicate review IDs
    df = df.drop_duplicates(subset=["review_id"])

    # Convert rating to numeric
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df[df["rating"].between(1, 5)]

    # Normalize branch and platform names
    df["branch"] = df["branch"].astype(str).str.strip()
    df["platform"] = df["platform"].astype(str).str.strip()

    # Convert review dates
    df["review_date"] = pd.to_datetime(
        df["review_date"], errors="coerce"
    )
    df = df.dropna(subset=["review_date"])

    return df.reset_index(drop=True)


def preprocess_operations(df):

    missing = set(OPERATIONS_REQUIRED_COLUMNS) - set(df.columns)

    if missing:
        raise ValueError(f"Missing operational columns: {missing}")

    df = df.copy()

    numeric_columns = [
        "orders_count",
        "staff_count",
        "avg_order_prep_time_minutes",
        "refunds_count"
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=numeric_columns)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    df = df[
        (df["orders_count"] >= 0) &
        (df["staff_count"] >= 0) &
        (df["avg_order_prep_time_minutes"] >= 0) &
        (df["refunds_count"] >= 0)
    ]

    df["branch"] = df["branch"].astype(str).str.strip()

    return df.reset_index(drop=True)
