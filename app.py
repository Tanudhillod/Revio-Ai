
import streamlit as st
import pandas as pd
import plotly.express as px

from modules.preprocessing import load_reviews, load_operations
from modules.ai_analyzer import analyze_reviews
from modules.analytics import (
    generate_overview,
    get_theme_analysis,
    get_branch_analysis,
    get_daily_trends
)
from modules.root_cause import generate_root_cause_report
from modules.recommendations import (
    generate_recommendations,
    save_recommendations
)


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Revio AI | Root Cause Intelligence",
    page_icon="🔍",
    layout="wide"
)


# --------------------------------------------------
# CUSTOM STYLING
# --------------------------------------------------

st.markdown("""
<style>
    .main {
        background-color: #f8fafc;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    .main-title {
        font-size: 2.3rem;
        font-weight: 750;
        color: #172554;
    }

    .subtitle {
        color: #64748b;
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "analyzed_reviews" not in st.session_state:
    st.session_state.analyzed_reviews = None

if "root_cause_report" not in st.session_state:
    st.session_state.root_cause_report = None

if "recommendations" not in st.session_state:
    st.session_state.recommendations = None

if "operations" not in st.session_state:
    st.session_state.operations = None


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    '<div class="main-title">Revio AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Root Cause Intelligence | Turning customer feedback '
    'into operational improvements'
    '</div>',
    unsafe_allow_html=True
)

st.divider()


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.title("Revio AI")

st.sidebar.markdown("### Upload your data")

reviews_file = st.sidebar.file_uploader(
    "Upload Reviews CSV",
    type=["csv"],
    key="reviews_upload"
)

operations_file = st.sidebar.file_uploader(
    "Upload Operations CSV",
    type=["csv"],
    key="operations_upload"
)

st.sidebar.divider()

st.sidebar.markdown("### Analysis settings")

max_reviews = st.sidebar.slider(
    "Number of reviews to analyze",
    min_value=5,
    max_value=240,
    value=20,
    step=5
)

st.sidebar.caption(
    "The review limit controls how many reviews "
    "are sent to Gemini. Increase it for a fuller analysis."
)


# --------------------------------------------------
# RUN ANALYSIS
# --------------------------------------------------

st.header("Data Analysis")

if reviews_file is None:

    st.info(
        "Upload your reviews CSV from the sidebar to get started."
    )

else:

    if st.button(
        "Run AI Analysis",
        type="primary",
        use_container_width=True
    ):

        try:

            with st.spinner("Loading and validating data..."):

                reviews = load_reviews(reviews_file)

                operations = None

                if operations_file is not None:
                    operations = load_operations(
                        operations_file
                    )

                st.session_state.operations = operations

            with st.spinner(
                "Gemini is analyzing customer reviews..."
            ):

                analyzed = analyze_reviews(
                    reviews,
                    batch_size=5,
                    max_reviews=max_reviews
                )

                st.session_state.analyzed_reviews = analyzed

            st.session_state.root_cause_report = None
            st.session_state.recommendations = None

            st.success(
                f"Successfully analyzed {len(analyzed)} reviews!"
            )

        except Exception as e:

            st.error(f"Analysis failed: {str(e)}")


# --------------------------------------------------
# DISPLAY RESULTS
# --------------------------------------------------

analyzed_reviews = st.session_state.analyzed_reviews
operations = st.session_state.operations

if analyzed_reviews is not None:

    st.divider()

    st.header("1. Review Intelligence")

    # OVERVIEW METRICS

    overview = generate_overview(analyzed_reviews)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Reviews",
        overview["total_reviews"]
    )

    col2.metric(
        "Average Rating",
        round(overview["average_rating"], 2)
    )

    col3.metric(
        "Negative Reviews",
        overview["negative_reviews"]
    )

    col4.metric(
        "Negative Review %",
        f'{overview["negative_percentage"]:.1f}%'
    )

    st.divider()

    # SENTIMENT ANALYSIS

    st.subheader("Sentiment Distribution")

    sentiment_counts = (
        analyzed_reviews["sentiment"]
        .value_counts()
        .reset_index()
    )

    sentiment_counts.columns = [
        "Sentiment",
        "Count"
    ]

    fig_sentiment = px.pie(
        sentiment_counts,
        names="Sentiment",
        values="Count",
        hole=0.55,
        title="Customer Sentiment"
    )

    st.plotly_chart(
        fig_sentiment,
        use_container_width=True
    )

    # THEME ANALYSIS

    st.subheader("Customer Complaint Themes")

    theme_data = get_theme_analysis(
        analyzed_reviews
    )

    if not theme_data.empty:

        st.dataframe(
            theme_data,
            use_container_width=True,
            hide_index=True
        )

        if (
            "theme" in theme_data.columns
            and "count" in theme_data.columns
        ):

            fig_theme = px.bar(
                theme_data,
                x="theme",
                y="count",
                title="Reviews by Theme",
                labels={
                    "theme": "Theme",
                    "count": "Number of Reviews"
                }
            )

            st.plotly_chart(
                fig_theme,
                use_container_width=True
            )

    # BRANCH ANALYSIS

    st.subheader("Branch Performance")

    branch_data = get_branch_analysis(
        analyzed_reviews
    )

    st.dataframe(
        branch_data,
        use_container_width=True,
        hide_index=True
    )

    if (
        "branch" in branch_data.columns
        and "negative_percentage" in branch_data.columns
    ):

        fig_branch = px.bar(
            branch_data,
            x="branch",
            y="negative_percentage",
            title="Negative Reviews by Branch",
            labels={
                "branch": "Branch",
                "negative_percentage": "Negative Reviews (%)"
            }
        )

        st.plotly_chart(
            fig_branch,
            use_container_width=True
        )

    # DAILY TRENDS

    st.subheader("Customer Feedback Trends")

    # Calculate daily trends directly from analyzed_reviews.
    # This avoids depending on the date-column name returned
    # by get_daily_trends() in analytics.py.

    if "review_date" in analyzed_reviews.columns:

        daily_source = analyzed_reviews.copy()

        daily_source["review_date"] = pd.to_datetime(
            daily_source["review_date"],
            errors="coerce"
        )

        daily_source = daily_source.dropna(
            subset=["review_date"]
        )

        if not daily_source.empty:

            daily_source["review_date"] = (
                daily_source["review_date"].dt.date
            )

            daily_data = (
                daily_source.groupby("review_date")
                .agg(
                    total_reviews=("review_id", "count"),
                    negative_reviews=(
                        "sentiment",
                        lambda values: (values == "Negative").sum()
                    )
                )
                .reset_index()
                .sort_values("review_date")
            )

            daily_data["review_date"] = pd.to_datetime(
                daily_data["review_date"]
            )

            st.line_chart(
                daily_data.set_index("review_date")[
                    ["total_reviews", "negative_reviews"]
                ]
            )

        else:

            st.info(
                "No valid review dates are available to display trends."
            )

    else:

        st.warning(
            "The analyzed reviews do not contain a 'review_date' column. "
            "Please check your uploaded reviews CSV."
        )

    # REVIEW TABLE

    with st.expander("View Analyzed Customer Reviews"):

        st.dataframe(
            analyzed_reviews,
            use_container_width=True,
            hide_index=True
        )

    st.download_button(
        "Download Analyzed Reviews",
        data=analyzed_reviews.to_csv(index=False),
        file_name="analyzed_reviews.csv",
        mime="text/csv"
    )



    # --------------------------------------------------
    # ROOT CAUSE INTELLIGENCE
    # --------------------------------------------------

    st.divider()

    st.header("2. Root Cause Intelligence")

    if operations is None:

        st.warning(
            "Upload the operations CSV to investigate "
            "possible operational risk factors."
        )

    else:

        if st.button(
            "Investigate Operational Risks",
            use_container_width=True
        ):

            try:

                with st.spinner(
                    "Comparing customer feedback with operational data..."
                ):

                    report = generate_root_cause_report(
                        analyzed_reviews,
                        operations
                    )

                    st.session_state.root_cause_report = report
                    st.session_state.recommendations = None

                st.success(
                    "Operational investigation completed!"
                )

            except Exception as e:

                st.error(
                    f"Root cause investigation failed: {str(e)}"
                )

        report = st.session_state.root_cause_report

        if report is not None:

            # INVESTIGATION FINDINGS

            findings = report.get("findings", [])

            st.subheader("Investigation Findings")

            if isinstance(findings, pd.DataFrame):

                if not findings.empty:
                    st.dataframe(
                        findings,
                        use_container_width=True,
                        hide_index=True
                    )

            elif isinstance(findings, list) and len(findings) > 0:

                st.dataframe(
                    pd.DataFrame(findings),
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info(
                    "No investigation findings were generated."
                )

            # OPERATIONAL RISK ANALYSIS

            risk_analysis = report.get(
                "risk_analysis",
                pd.DataFrame()
            )

            if isinstance(risk_analysis, pd.DataFrame):

                if not risk_analysis.empty:

                    st.subheader("Operational Risk Analysis")

                    st.dataframe(
                        risk_analysis,
                        use_container_width=True,
                        hide_index=True
                    )

            # OPERATIONAL CORRELATIONS

            correlations = report.get("correlations")

            if correlations is not None:

                if isinstance(correlations, pd.DataFrame):

                    if not correlations.empty:

                        st.subheader("Operational Correlations")

                        st.dataframe(
                            correlations,
                            use_container_width=True,
                            hide_index=True
                        )

                elif isinstance(correlations, (dict, list)):

                    if len(correlations) > 0:

                        st.subheader("Operational Correlations")

                        st.json(correlations)

            # COMPLAINT PATTERNS

            complaints = report.get("complaints")

            if isinstance(complaints, pd.DataFrame):

                if not complaints.empty:

                    st.subheader("Complaint Patterns")

                    st.dataframe(
                        complaints,
                        use_container_width=True,
                        hide_index=True
                    )

            elif isinstance(complaints, list) and len(complaints) > 0:

                st.subheader("Complaint Patterns")

                st.dataframe(
                    pd.DataFrame(complaints),
                    use_container_width=True,
                    hide_index=True
                )

            # --------------------------------------------------
            # AI RECOMMENDATIONS
            # --------------------------------------------------

            st.divider()

            st.header("3. AI-Powered Recommendations")

            if st.button(
                "Generate Action Plan",
                type="primary",
                use_container_width=True
            ):

                try:

                    with st.spinner(
                        "Gemini is preparing an evidence-based action plan..."
                    ):

                        recommendations = generate_recommendations(
                            report,
                            analyzed_reviews
                        )

                        st.session_state.recommendations = (
                            recommendations
                        )

                    st.success(
                        "Recommendations generated successfully!"
                    )

                except Exception as e:

                    st.error(
                        f"Recommendation generation failed: {str(e)}"
                    )

            recommendations = st.session_state.recommendations

            if (
                isinstance(recommendations, list)
                and len(recommendations) > 0
            ):

                for index, item in enumerate(recommendations):

                    with st.container(border=True):

                        st.subheader(
                            f'{item["branch"]} — {item["problem"]}'
                        )

                        priority = item["priority"]

                        if priority == "High":
                            st.error("High Priority")

                        elif priority == "Medium":
                            st.warning("Medium Priority")

                        else:
                            st.info("Low Priority")

                        st.markdown("**Evidence**")
                        st.write(item["evidence_summary"])

                        st.markdown("**Possible Explanations**")

                        for explanation in item["possible_explanations"]:
                            st.write(f"• {explanation}")

                        st.markdown("**Recommended Actions**")

                        for action in item["recommended_actions"]:
                            st.write(f"✓ {action}")

                        st.markdown("**Success Metrics**")

                        for metric in item["success_metrics"]:
                            st.write(f"• {metric}")

                        st.markdown("**Further Validation Needed**")
                        st.write(item["validation_needed"])

                # DOWNLOAD RECOMMENDATIONS

                recommendations_df = pd.DataFrame(
                    recommendations
                )

                for column in [
                    "possible_explanations",
                    "recommended_actions",
                    "success_metrics"
                ]:

                    if column in recommendations_df.columns:

                        recommendations_df[column] = (
                            recommendations_df[column].apply(
                                lambda values: " | ".join(values)
                                if isinstance(values, list)
                                else str(values)
                            )
                        )

                st.download_button(
                    "Download Recommendations",
                    data=recommendations_df.to_csv(index=False),
                    file_name="revio_ai_recommendations.csv",
                    mime="text/csv"
                )
