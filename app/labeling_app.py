import streamlit as st
import polars as pl
import duckdb
from datetime import datetime
import os
import logging
from dotenv import load_dotenv
import altair as alt
import re
import uuid

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the data directory and database path
DATA_DIR = os.path.join(os.getcwd(), "data")
DATABASE_PATH = os.path.join(DATA_DIR, "labeling_data.db")

# Create the data directory if it doesn't exist
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    logger.info(f"Created data directory at {DATA_DIR}")

# Check if the database file exists, and reinitialize if not
if not os.path.exists(DATABASE_PATH):
    logger.info("Database file not found. Reinitializing the database.")
    conn = duckdb.connect(DATABASE_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS labels (
        text STRING,
        label STRING,
        timestamp TIMESTAMP,
        batch_id STRING,
        batch_name STRING
    )
    """)
else:
    conn = duckdb.connect(DATABASE_PATH)


# Function to save labels to the database
def save_labels(labels, batch_id, batch_name):
    try:
        timestamp = datetime.now()
        for label in labels:
            label["timestamp"] = timestamp
            label["batch_id"] = batch_id
            label["batch_name"] = batch_name
        df = pl.DataFrame(labels)
        conn.execute("INSERT INTO labels SELECT * FROM df")
        logger.info("Labels saved successfully.")
    except Exception as e:
        logger.error(f"Error saving labels: {e}")


# Caching the CSV loading function
@st.cache_data
def load_data_from_csv(uploaded_file):
    try:
        batch_name = uploaded_file.name
        batch_id = str(uuid.uuid4())
        df = pl.read_csv(uploaded_file)
        df = df.with_columns(
            [pl.lit(batch_id).alias("batch_id"), pl.lit(batch_name).alias("batch_name")]
        )
        return df
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        return pl.DataFrame()


# Function to fetch the latest 500 labels from the database
def fetch_latest_labels(limit=500):
    try:
        query = f"SELECT text, label, timestamp, batch_id, batch_name FROM labels ORDER BY timestamp DESC LIMIT {limit}"
        return conn.execute(query).fetchdf()
    except Exception as e:
        logger.error(f"Error fetching labels: {e}")
        return pl.DataFrame()


# Validate custom batch name
def validate_batch_name(name):
    return re.match(r"^[a-z0-9_-]+$", name) is not None


# Initialize session state
if "labels" not in st.session_state:
    st.session_state.labels = []
if "selected_indices" not in st.session_state:
    st.session_state.selected_indices = set()
if "current_page" not in st.session_state:
    st.session_state.current_page = 0
if "saved_pages" not in st.session_state:
    st.session_state.saved_pages = set()
if "custom_labels" not in st.session_state:
    st.session_state.custom_labels = ["Positive", "Negative", "Unsure"]

# Constants
PAGE_SIZE = 100

# Streamlit App
st.set_page_config(layout="wide")
st.title("NLP Text Labeling App")

# Sidebar for custom labels
st.sidebar.subheader("Custom Labels")
custom_labels_input = st.sidebar.text_input(
    "Enter labels separated by commas", ",".join(st.session_state.custom_labels)
)
if st.sidebar.button("Update Labels"):
    st.session_state.custom_labels = [
        label.strip() for label in custom_labels_input.split(",")
    ]

# File uploader for CSV (single file only)
uploaded_file = st.file_uploader(
    "Upload a CSV file", type="csv", accept_multiple_files=False
)

# Load data
if uploaded_file:
    # Reset state when a new file is uploaded
    data = load_data_from_csv(uploaded_file)
else:
    data = pl.DataFrame()

if not data.is_empty():
    total_pages = (len(data) + PAGE_SIZE - 1) // PAGE_SIZE

    # Sidebar navigation and labeling controls
    st.sidebar.subheader("Navigation")
    if st.sidebar.button("Previous Page", key="prev_page"):
        st.session_state.current_page = max(0, st.session_state.current_page - 1)
    if st.sidebar.button("Next Page", key="next_page"):
        st.session_state.current_page = min(
            total_pages - 1, st.session_state.current_page + 1
        )

    # Indicate saved pages with a green tick
    saved_status = (
        " ✅" if st.session_state.current_page in st.session_state.saved_pages else ""
    )
    st.sidebar.write(
        f"Page {st.session_state.current_page + 1} of {total_pages}{saved_status}"
    )

    # Display current page data
    start_idx = st.session_state.current_page * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, len(data))
    page_data = data[start_idx:end_idx]

    # Labeling controls
    st.sidebar.subheader("Labeling Controls")
    if st.sidebar.button("Select All", help="Select all texts on the current page"):
        st.session_state.selected_indices.update(range(start_idx, end_idx))
    if st.sidebar.button("Unselect All", help="Unselect all texts on the current page"):
        st.session_state.selected_indices.difference_update(range(start_idx, end_idx))
    if st.sidebar.button(
        "Invert Selection", help="Invert the selection of texts on the current page"
    ):
        all_indices = set(range(start_idx, end_idx))
        st.session_state.selected_indices.symmetric_difference_update(all_indices)

    # Bulk labeling and save labels
    st.sidebar.subheader("Bulk Actions")
    bulk_label = st.sidebar.selectbox(
        "Select a label to apply to selected texts", st.session_state.custom_labels
    )
    if st.sidebar.button(
        "Apply Bulk Label", help="Apply the selected label to all selected texts"
    ):
        for index in st.session_state.selected_indices:
            st.session_state.labels[index]["label"] = bulk_label
        st.success(f"Applied '{bulk_label}' to selected texts.")

    if st.sidebar.button("Save Labels", help="Save the labels for the current page"):
        batch_id = str(uuid.uuid4())
        batch_name = (
            page_data["batch_name"][0]
            if "batch_name" in page_data.columns
            else "unknown"
        )
        save_labels(st.session_state.labels, batch_id, batch_name)
        st.session_state.saved_pages.add(
            st.session_state.current_page
        )  # Mark the current page as saved
        st.success("Labels saved!")

    # Export options
    st.sidebar.subheader("Export Labeled Data")
    export_format = st.sidebar.selectbox(
        "Select export format", ["CSV", "JSON", "Parquet"]
    )
    if st.sidebar.button(
        "Export", help="Export the labeled data in the selected format"
    ):
        saved_labels = fetch_latest_labels()
        export_data = saved_labels.to_pandas()  # Convert to pandas for export
        if export_format == "CSV":
            st.download_button(
                "Download CSV",
                export_data.to_csv(index=False),
                file_name="labeled_data.csv",
            )
        elif export_format == "JSON":
            st.download_button(
                "Download JSON",
                export_data.to_json(orient="records"),
                file_name="labeled_data.json",
            )
        elif export_format == "Parquet":
            st.download_button(
                "Download Parquet",
                export_data.to_parquet(),
                file_name="labeled_data.parquet",
            )

    st.subheader("Label Individual Texts")
    for index, row in enumerate(page_data.iter_rows(named=True), start=start_idx):
        col1, col2, col3 = st.columns([0.1, 3, 1])
        with col1:
            selected = st.checkbox(
                "Select",
                key=f"select_{index}",
                value=index in st.session_state.selected_indices,
                label_visibility="collapsed",
            )
            if selected:
                st.session_state.selected_indices.add(index)
            else:
                st.session_state.selected_indices.discard(index)
        with col2:
            st.text_area(
                f"Text {index + 1}",
                value=row["text"],
                height=100,
                key=f"text_{index}",
                disabled=True,
            )
        with col3:
            label = st.selectbox(
                f"Label for text {index + 1}",
                st.session_state.custom_labels,
                key=f"label_{index}",
                index=0
                if index >= len(st.session_state.labels)
                else st.session_state.custom_labels.index(
                    st.session_state.labels[index]["label"]
                ),
            )
            if index >= len(st.session_state.labels):
                st.session_state.labels.append({"text": row["text"], "label": label})
            else:
                st.session_state.labels[index]["label"] = label

    # Show saved labels
    st.subheader("Latest 500 Saved Labels")
    saved_labels = fetch_latest_labels()
    st.dataframe(saved_labels, use_container_width=True)

    # Data visualization
    st.subheader("Label Distribution")
    if not saved_labels.empty:
        label_counts = saved_labels["label"].value_counts().reset_index()
        label_counts.columns = ["label", "count"]
        chart = (
            alt.Chart(label_counts)
            .mark_bar()
            .encode(x="label", y="count", color="label")
        )
        st.altair_chart(chart, use_container_width=True)
else:
    st.info("Please upload a CSV file to start labeling.")
