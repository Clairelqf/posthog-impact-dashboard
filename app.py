import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from collections import Counter

st.set_page_config(page_title="PostHog Engineering Impact", layout="wide")
REPO = "PostHog/posthog"
API_URL = "https://api.github.com/search/issues"

GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

st.title("🦔 PostHog Engineering Impact Dashboard")
st.markdown("""
**Audience:** PostHog Engineering Leadership  
**Definition of Impact:** For this MVP, impact is calculated over the last 30 days using a blended score of **Execution** (Merged PRs) and **Problem Solving** (Closed Issues). 
*Pragmatism note: PR Reviews were excluded to avoid GitHub API rate limits during the 1-hour build window.*
""")

@st.cache_data(ttl=3600)
def fetch_github_data(query, days=30):
    """Fetches data from GitHub Search API based on a query."""
    since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    full_query = f"repo:{REPO} {query} updated:>{since_date}"
    
    response = requests.get(f"{API_URL}?q={full_query}&per_page=100", headers=HEADERS)
    if response.status_code != 200:
        st.error(f"API Error: {response.status_code}. You may need a GitHub Token.")
        return []
    
    return response.json().get('items', [])

with st.spinner("Fetching data from PostHog repository..."):
    # Fetch Merged PRs
    prs = fetch_github_data("is:pr is:merged")
    # Fetch Closed Issues
    issues = fetch_github_data("is:issue is:closed")

# --- DATA PROCESSING ---
if prs or issues:
    # Count PRs per user (excluding bots)
    pr_counts = Counter([pr['user']['login'] for pr in prs if '[bot]' not in pr['user']['login']])
    # Count Issues per user
    issue_counts = Counter([issue['user']['login'] for issue in issues if '[bot]' not in issue['user']['login']])
    
    # Combine into a DataFrame
    all_users = set(pr_counts.keys()).union(set(issue_counts.keys()))
    data = []
    for user in all_users:
        pr_score = pr_counts.get(user, 0)
        issue_score = issue_counts.get(user, 0)
        # Weight PRs slightly higher than issues for the final score
        impact_score = (pr_score * 1.5) + (issue_score * 1.0)
        
        data.append({
            "Engineer": user,
            "Merged PRs": pr_score,
            "Closed Issues": issue_score,
            "Impact Score": impact_score
        })
        
    df = pd.DataFrame(data).sort_values(by="Impact Score", ascending=False).head(5)
    df.index = df.index + 1

    st.subheader("🏆 Top 5 Most Impactful Engineers (Last 30 Days)")
    
    cols = st.columns(5)
    for i, (index, row) in enumerate(df.iterrows()):
        with cols[i]:
            st.metric(label=f"#{i+1} {row['Engineer']}", value=f"{row['Impact Score']} pts")
            
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Impact Breakdown")
        st.bar_chart(df.set_index("Engineer")[["Merged PRs", "Closed Issues"]])
    with col2:
        st.markdown("### Raw Data")
        st.dataframe(df, use_container_width=True)
else:
    st.warning("No data fetched. Check your rate limits or API token.")