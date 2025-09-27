"""
CORD-19 Research Papers Dashboard
Interactive Streamlit app for exploring COVID-19 research literature
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import re
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="CORD-19 Research Dashboard",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #ff7f0e;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #1f77b4;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# Title and description
st.markdown('<h1 class="main-header">🦠 CORD-19 Research Papers Dashboard</h1>', unsafe_allow_html=True)
st.markdown("""
**Welcome to the COVID-19 Open Research Dataset (CORD-19) Analysis Dashboard!**

This interactive dashboard allows you to explore thousands of research papers related to COVID-19 and coronavirus research. 
Use the controls in the sidebar to filter and analyze the data in different ways.

---
""")

@st.cache_data
def load_data():
    """Load and preprocess the CORD-19 dataset with caching for performance."""
    try:
        # Load the dataset - using raw string to handle Windows paths properly
        # Option 1: Use raw string (r'...')
        df = pd.read_csv('metadata.csv')
        
        # Alternative options you can use instead:
        # Option 2: Use forward slashes
        # df = pd.read_csv('D:/PLP/Phase 1 Fundamentals/Python/Week 8 Python Frameworks/cord19_analysis/data/metadata.csv')
        
        # Option 3: Use relative path (recommended - place metadata.csv in same folder as app.py)
        # df = pd.read_csv('metadata.csv')
        
        # Basic cleaning
        df = df.dropna(subset=['title'])  # Remove rows without titles
        
        # Fill missing values
        df['journal'] = df['journal'].fillna('Unknown Journal')
        df['authors'] = df['authors'].fillna('Unknown Authors')
        if 'source_x' in df.columns:
            df['source_x'] = df['source_x'].fillna('Unknown Source')
        
        # Convert publish_time to datetime and extract year
        if 'publish_time' in df.columns:
            df['publish_time'] = pd.to_datetime(df['publish_time'], errors='coerce')
            df['publish_year'] = df['publish_time'].dt.year
            df = df.dropna(subset=['publish_year'])
            df['publish_year'] = df['publish_year'].astype(int)
        
        # Add word counts
        if 'abstract' in df.columns:
            df['abstract_word_count'] = df['abstract'].apply(
                lambda x: len(str(x).split()) if pd.notna(x) else 0
            )
        
        df['title_word_count'] = df['title'].apply(
            lambda x: len(str(x).split()) if pd.notna(x) else 0
        )
        
        return df
        
    except FileNotFoundError:
        st.error("❌ metadata.csv file not found! Please ensure the file is in the same directory as this app.")
        return None
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        return None

# Load data
with st.spinner("Loading CORD-19 dataset... This may take a moment."):
    df = load_data()

if df is not None:
    # Sidebar controls
    st.sidebar.header("🎛️ Dashboard Controls")
    st.sidebar.markdown("Use these controls to filter and explore the data:")
    
    # Year range selector
    if 'publish_year' in df.columns:
        year_min, year_max = int(df['publish_year'].min()), int(df['publish_year'].max())
        year_range = st.sidebar.slider(
            "📅 Select Year Range",
            min_value=max(2000, year_min),  # Start from 2000 for cleaner display
            max_value=min(2024, year_max),  # End at 2024 for current relevance
            value=(max(2000, year_min), min(2024, year_max)),
            help="Filter papers by publication year"
        )
    else:
        year_range = None
    
    # Journal selector
    if 'journal' in df.columns:
        top_journals = df['journal'].value_counts().head(20).index.tolist()
        if 'Unknown Journal' in top_journals:
            top_journals.remove('Unknown Journal')
        
        selected_journals = st.sidebar.multiselect(
            "📰 Select Journals (Top 20)",
            options=top_journals,
            default=top_journals[:5],  # Select top 5 by default
            help="Choose specific journals to analyze"
        )
    else:
        selected_journals = []
    
    # Source selector
    if 'source_x' in df.columns:
        available_sources = df['source_x'].unique().tolist()
        if 'Unknown Source' in available_sources:
            available_sources.remove('Unknown Source')
        
        selected_sources = st.sidebar.multiselect(
            "📚 Select Data Sources",
            options=available_sources,
            default=available_sources[:3] if len(available_sources) > 3 else available_sources,
            help="Filter by data source"
        )
    else:
        selected_sources = []
    
    # Abstract length filter
    if 'abstract_word_count' in df.columns:
        abstract_min, abstract_max = int(df['abstract_word_count'].min()), int(df['abstract_word_count'].max())
        abstract_range = st.sidebar.slider(
            "📝 Abstract Length (words)",
            min_value=0,
            max_value=min(1000, abstract_max),  # Cap at 1000 for practical purposes
            value=(0, min(500, abstract_max)),
            help="Filter papers by abstract length"
        )
    else:
        abstract_range = None
    
    # Apply filters
    filtered_df = df.copy()
    
    if year_range and 'publish_year' in df.columns:
        filtered_df = filtered_df[
            (filtered_df['publish_year'] >= year_range[0]) & 
            (filtered_df['publish_year'] <= year_range[1])
        ]
    
    if selected_journals and 'journal' in df.columns:
        filtered_df = filtered_df[filtered_df['journal'].isin(selected_journals)]
    
    if selected_sources and 'source_x' in df.columns:
        filtered_df = filtered_df[filtered_df['source_x'].isin(selected_sources)]
    
    if abstract_range and 'abstract_word_count' in df.columns:
        filtered_df = filtered_df[
            (filtered_df['abstract_word_count'] >= abstract_range[0]) & 
            (filtered_df['abstract_word_count'] <= abstract_range[1])
        ]
    
    # Display key metrics
    st.markdown('<h2 class="sub-header">📊 Key Metrics</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📄 Total Papers",
            value=f"{len(filtered_df):,}",
            delta=f"{len(filtered_df) - len(df):,}" if len(filtered_df) != len(df) else None
        )
    
    with col2:
        if 'journal' in filtered_df.columns:
            unique_journals = filtered_df['journal'].nunique()
            st.metric(
                label="📰 Unique Journals",
                value=f"{unique_journals:,}"
            )
    
    with col3:
        if 'publish_year' in filtered_df.columns:
            year_span = filtered_df['publish_year'].max() - filtered_df['publish_year'].min() + 1
            st.metric(
                label="📅 Year Span",
                value=f"{year_span} years"
            )
    
    with col4:
        if 'abstract_word_count' in filtered_df.columns:
            avg_abstract_length = filtered_df['abstract_word_count'].mean()
            st.metric(
                label="📝 Avg Abstract Length",
                value=f"{avg_abstract_length:.0f} words"
            )
    
    # Main visualizations
    st.markdown('<h2 class="sub-header">📈 Visualizations</h2>', unsafe_allow_html=True)
    
    # Create tabs for different visualizations
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Publications Over Time", "📰 Top Journals", "☁️ Title Word Cloud", "📚 Data Sources"])
    
    with tab1:
        st.subheader("Publications by Year")
        
        if 'publish_year' in filtered_df.columns and len(filtered_df) > 0:
            # Create yearly publication counts
            yearly_counts = filtered_df['publish_year'].value_counts().sort_index()
            
            # Create interactive plot with Plotly
            fig = px.bar(
                x=yearly_counts.index,
                y=yearly_counts.values,
                title="Number of Publications per Year",
                labels={'x': 'Year', 'y': 'Number of Publications'},
                color=yearly_counts.values,
                color_continuous_scale='viridis'
            )
            
            fig.update_layout(
                height=500,
                showlegend=False,
                xaxis_title="Year",
                yaxis_title="Number of Publications"
            )
            
            # Highlight 2020 if present (COVID-19 peak year)
            if 2020 in yearly_counts.index:
                fig.add_annotation(
                    x=2020,
                    y=yearly_counts[2020],
                    text="COVID-19 Peak",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="red",
                    font=dict(color="red", size=12)
                )
            
            st.plotly_chart(fig, width='stretch')
            
            # Show trend insights
            if len(yearly_counts) > 1:
                peak_year = yearly_counts.idxmax()
                peak_count = yearly_counts.max()
                st.info(f"📈 **Peak Publication Year:** {peak_year} with {peak_count:,} papers")
        else:
            st.warning("No data available for the selected filters.")
    
    with tab2:
        st.subheader("Top Journals by Publication Count")
        
        if 'journal' in filtered_df.columns and len(filtered_df) > 0:
            top_journals_data = filtered_df['journal'].value_counts().head(15)
            
            # Remove 'Unknown Journal' if present
            if 'Unknown Journal' in top_journals_data.index:
                top_journals_data = top_journals_data.drop('Unknown Journal')
            
            if len(top_journals_data) > 0:
                fig = px.bar(
                    x=top_journals_data.values,
                    y=top_journals_data.index,
                    orientation='h',
                    title="Top 15 Journals by Publication Count",
                    labels={'x': 'Number of Publications', 'y': 'Journal'},
                    color=top_journals_data.values,
                    color_continuous_scale='plasma'
                )
                
                fig.update_layout(
                    height=600,
                    showlegend=False,
                    yaxis={'categoryorder': 'total ascending'}
                )
                
                st.plotly_chart(fig, width='stretch')
                
                # Show top journal insight
                top_journal = top_journals_data.index[0]
                top_count = top_journals_data.iloc[0]
                st.info(f"📰 **Top Journal:** {top_journal} with {top_count:,} papers")
            else:
                st.warning("No journal data available for the selected filters.")
        else:
            st.warning("No journal data available.")
    
    with tab3:
        st.subheader("Most Common Words in Paper Titles")
        
        if 'title' in filtered_df.columns and len(filtered_df) > 0:
            # Extract words from titles
            all_titles = ' '.join(filtered_df['title'].dropna().astype(str))
            
            # Clean and extract words
            words = re.findall(r'\b[a-zA-Z]{4,}\b', all_titles.lower())  # Words with 4+ characters
            
            # Remove common stop words
            stop_words = {
                'the', 'and', 'for', 'are', 'with', 'this', 'that', 'from', 'they', 'been',
                'have', 'were', 'said', 'each', 'which', 'their', 'time', 'will', 'about',
                'would', 'there', 'could', 'other', 'after', 'first', 'well', 'many', 'some',
                'what', 'only', 'when', 'than', 'than', 'also', 'much', 'very', 'most',
                'such', 'more', 'these', 'those', 'into', 'should', 'over', 'between',
                'through', 'during', 'before', 'after', 'above', 'below', 'down', 'under'
            }
            
            # Filter words
            filtered_words = [word for word in words if word not in stop_words]
            
            if filtered_words:
                # Word frequency
                word_freq = Counter(filtered_words)
                top_words = dict(word_freq.most_common(20))
                
                # Create two columns - word cloud and bar chart
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    try:
                        # Generate word cloud
                        wordcloud = WordCloud(
                            width=800,
                            height=400,
                            background_color='white',
                            max_words=100,
                            colormap='viridis'
                        ).generate_from_frequencies(word_freq)
                        
                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.imshow(wordcloud, interpolation='bilinear')
                        ax.axis('off')
                        ax.set_title('Word Cloud of Paper Titles', fontsize=16, fontweight='bold', pad=20)
                        
                        st.pyplot(fig)
                        
                    except ImportError:
                        st.warning("WordCloud library not available. Showing top words as bar chart instead.")
                        
                        # Alternative: horizontal bar chart
                        fig = px.bar(
                            x=list(top_words.values())[:15],
                            y=list(top_words.keys())[:15],
                            orientation='h',
                            title="Top 15 Words in Titles",
                            labels={'x': 'Frequency', 'y': 'Words'}
                        )
                        fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                        st.plotly_chart(fig, width='stretch')
                
                with col2:
                    st.write("**Top 10 Words:**")
                    top_10 = list(top_words.items())[:10]
                    for i, (word, count) in enumerate(top_10, 1):
                        st.write(f"{i}. **{word}**: {count:,}")
                
                # Show insight
                most_common = list(top_words.keys())[0]
                most_count = list(top_words.values())[0]
                st.info(f"🔤 **Most Common Word:** '{most_common}' appears {most_count:,} times in titles")
            
            else:
                st.warning("No words found in titles for analysis.")
        else:
            st.warning("No title data available.")
    
    with tab4:
        st.subheader("Distribution by Data Source")
        
        if 'source_x' in filtered_df.columns and len(filtered_df) > 0:
            source_counts = filtered_df['source_x'].value_counts()
            
            # Remove 'Unknown Source' if present
            if 'Unknown Source' in source_counts.index:
                source_counts = source_counts.drop('Unknown Source')
            
            if len(source_counts) > 0:
                # Create pie chart
                fig = px.pie(
                    values=source_counts.values,
                    names=source_counts.index,
                    title="Distribution of Papers by Data Source"
                )
                
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(height=500)
                
                st.plotly_chart(fig, width='stretch')
                
                # Show source breakdown
                st.write("**Source Breakdown:**")
                for source, count in source_counts.items():
                    percentage = (count / len(filtered_df)) * 100
                    st.write(f"- **{source}**: {count:,} papers ({percentage:.1f}%)")
            
            else:
                st.warning("No source data available for the selected filters.")
        else:
            st.warning("No source data available.")
    
    # Data sample section
    st.markdown('<h2 class="sub-header">🔍 Sample of Filtered Dataset</h2>', unsafe_allow_html=True)
    
    if len(filtered_df) > 0:
        # Show sample data
        display_columns = ['title', 'authors', 'journal', 'publish_year']
        if 'abstract' in filtered_df.columns:
            display_columns.append('abstract')
        
        # Only show columns that exist
        available_display_cols = [col for col in display_columns if col in filtered_df.columns]
        
        st.write(f"**Showing 10 random samples from {len(filtered_df):,} filtered papers:**")
        
        # Show random sample
        sample_df = filtered_df[available_display_cols].sample(n=min(10, len(filtered_df)))
        
        # Truncate long abstracts for display
        if 'abstract' in sample_df.columns:
            sample_df = sample_df.copy()
            sample_df['abstract'] = sample_df['abstract'].apply(
                lambda x: str(x)[:200] + "..." if pd.notna(x) and len(str(x)) > 200 else str(x)
            )
        
        st.dataframe(sample_df, width='stretch')
        
        # Download option
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv,
            file_name=f"cord19_filtered_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            help="Download the currently filtered dataset"
        )
    
    else:
        st.warning("⚠️ No data matches the current filter criteria. Please adjust your filters.")
    
    # Additional insights section
    if len(filtered_df) > 0:
        st.markdown('<h2 class="sub-header">💡 Quick Insights</h2>', unsafe_allow_html=True)
        
        insights = []
        
        # Publication trend insight
        if 'publish_year' in filtered_df.columns and len(filtered_df['publish_year'].unique()) > 1:
            recent_years = filtered_df[filtered_df['publish_year'] >= 2020]
            if len(recent_years) > 0:
                recent_percentage = (len(recent_years) / len(filtered_df)) * 100
                insights.append(f"📅 **{recent_percentage:.1f}%** of papers were published in 2020 or later")
        
        # Abstract length insight
        if 'abstract_word_count' in filtered_df.columns:
            papers_with_abstract = filtered_df[filtered_df['abstract_word_count'] > 0]
            if len(papers_with_abstract) > 0:
                avg_length = papers_with_abstract['abstract_word_count'].mean()
                insights.append(f"📝 Papers with abstracts average **{avg_length:.0f} words** in length")
        
        # Journal diversity insight
        if 'journal' in filtered_df.columns:
            unique_journals = filtered_df['journal'].nunique()
            total_papers = len(filtered_df)
            if unique_journals > 1:
                papers_per_journal = total_papers / unique_journals
                insights.append(f"📰 On average, each journal contributes **{papers_per_journal:.1f} papers**")
        
        # Display insights
        for insight in insights:
            st.write(insight)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    **About this Dashboard:**
    - Built with Streamlit and Python
    - Data source: CORD-19 Dataset (COVID-19 Open Research Dataset)
    - Interactive filtering and visualization capabilities
    - Real-time data analysis and insights
    
    **How to use:**
    1. Use the sidebar controls to filter the data
    2. Explore different tabs for various visualizations
    3. Download filtered data for further analysis
    
    ---
    *Dashboard created for educational and research purposes.*
    """)

else:
    st.error("""
    ## ❌ Unable to Load Data
    
    Please ensure that the `metadata.csv` file from the CORD-19 dataset is available in the same directory as this app.
    
    **Download Instructions:**
    1. Visit the [CORD-19 dataset page](https://www.semanticscholar.org/cord19/download)
    2. Download the metadata.csv file
    3. Place it in the same folder as this app.py file
    4. Restart the Streamlit app
    
    **File Requirements:**
    - File name must be exactly: `metadata.csv`
    - File should be in CSV format with proper headers
    - Recommended columns: title, authors, journal, publish_time, abstract, source_x
    """)

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.markdown("""
**💡 Tips:**
- Use filters to focus on specific time periods or journals
- Combine multiple filters for detailed analysis
- Download filtered data for offline analysis
- Refresh the page to reset all filters

**🔧 Technical Info:**
- Data cached for performance
- Interactive visualizations with Plotly
- Real-time filtering and analysis
""")

if df is not None:
    st.sidebar.markdown(f"""
    **📊 Current Data:**
    - Total papers: {len(df):,}
    - Filtered papers: {len(filtered_df):,}
    - Columns: {df.shape[1]}
    """)
else:
    st.sidebar.error("No data loaded")