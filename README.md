# Medfest_Nova

# Disease Surveillance Dashboard

This project integrates multiple public health data sources into a unified dataset for disease monitoring and analysis.

---

## Features

* Multi-source data integration:

  * Disease.sh (real-time COVID data)
  * CDC datasets
  * WHO datasets
  * ECDC
  * ProMED and HealthMap alerts
* Data cleaning and normalization
* Unified dataset stored in SQLite
* Backend ready for visualization/dashboard

---

## Requirements

* Python 3.10 or higher
* pip

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

---

### 2. Create a virtual environment

```bash
python3 -m venv venv
```

---

### 3. Activate the virtual environment

Linux / Mac:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

---

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is not available:

```bash
pip install pandas requests feedparser streamlit plotly
```

---

### 5. Run the backend

```bash
python backend.py
```

This will:

* Fetch data from all sources
* Clean and unify the dataset
* Store it in `disease_surveillance.db`

---
## Project Structure

```
backend.py          Data collection and cleaning
app.py              Streamlit dashboard
disease_surveillance.db
README.md
requirements.txt
```

---

## Output Format

The dataset contains:

```
country | disease | cases | deaths | year | source | alert
```

---

## Notes

* Some APIs may fail intermittently due to rate limits or availability.
* The system is designed to continue execution even if a data source fails.

---

## Authors

* Likhita Muddamsetty
* Vallari Jakileti
* Satya Pranavi Vemula
* Kundana Priya Muddireddy
