import streamlit as st
from google.cloud import storage
import pandas as pd
from io import BytesIO

BUCKET = "fantasysgpsystem-outputs"

@st.cache_data(ttl=300)
def list_files(prefix: str = ""):
    client = storage.Client()
    blobs = client.list_blobs(BUCKET, prefix=prefix)
    return sorted([b.name for b in blobs if b.name.lower().endswith((".csv", ".xlsx"))])

@st.cache_data(ttl=300)
def load_blob_to_df(blob_name: str) -> pd.DataFrame:
    client = storage.Client()
    b = client.bucket(BUCKET).blob(blob_name)
    data = b.download_as_bytes()
    if blob_name.lower().endswith(".csv"):
        return pd.read_csv(BytesIO(data))
    # Excel fallback
    return pd.read_excel(BytesIO(data), engine="openpyxl")

st.title("Fantasy SGP – File Viewer")

folder = st.selectbox("Folder", ["", "stats/", "ros/", "auction_calculator_exports/"])
files = list_files(prefix=folder)

if not files:
    st.info("No files found in that folder.")
else:
    pick = st.selectbox("Select file", files, index=len(files) - 1)
    st.caption(f"gs://{BUCKET}/{pick}")
    df = load_blob_to_df(pick)
    
    st.dataframe(df, use_container_width=True)

    # Offer CSV download regardless of original format
    out_name = pick.split("/")[-1].rsplit(".", 1)[0] + ".csv"
    st.download_button(
        "Download as CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name=out_name,
        mime="text/csv",
    )
