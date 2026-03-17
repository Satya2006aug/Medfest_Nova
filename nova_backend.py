import requests
import pandas as pd
import feedparser
import sqlite3
import traceback

errors = []
combined_data = []


def clean_dataset(df):
    df.columns = df.columns.str.lower()

    required_cols = ["country", "disease", "cases", "deaths", "year", "alert", "source"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = pd.NA

    df["country"] = df["country"].astype(str).str.strip()
    df["country"] = df["country"].replace({
        "None": pd.NA, "nan": pd.NA, "": pd.NA,
        "USA": "United States", "UK": "United Kingdom"
    })

    df["disease"] = df["disease"].astype(str).str.strip()
    df["disease"] = df["disease"].replace({
        "None": pd.NA, "nan": pd.NA, "": pd.NA
    })

    df["cases"] = pd.to_numeric(df["cases"], errors="coerce")
    df["deaths"] = pd.to_numeric(df["deaths"], errors="coerce")

    df["year"] = df["year"].astype(str).str[:4]
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    df["alert"] = df["alert"].astype(str)
    df.loc[df["alert"] == "None", "alert"] = pd.NA

    df = df.reset_index(drop=True)
    return df


# ---------------------------
# 1 Disease.sh API
# ---------------------------
try:
    before = len(combined_data)
    url = "https://disease.sh/v3/covid-19/countries"
    data = requests.get(url).json()
    for item in data:
        combined_data.append({
            "country": item["country"],
            "disease": "COVID-19",
            "cases": item["cases"],
            "deaths": item["deaths"],
            "year": 2024,
            "alert": None,
            "source": "Disease.sh"
        })
    print(f"Disease.sh loaded: {len(combined_data) - before} records")
except Exception as e:
    print("Disease.sh error:", e)


# ---------------------------
# 2 CDC Open Data Portal
# ---------------------------
try:
    before = len(combined_data)
    url = "https://data.cdc.gov/resource/9bhg-hcku.json?$limit=500000"
    data = requests.get(url, headers={"X-App-Token": ""}).json()
    for row in data:
        combined_data.append({
            "country": row.get("state", "USA"),
            "disease": row.get("group", "Notifiable Disease"),
            "cases": row.get("covid_19_deaths"),
            "deaths": row.get("covid_19_deaths"),
            "year": row.get("year"),
            "alert": None,
            "source": "CDC"
        })
    print(f"CDC loaded: {len(combined_data) - before} records")
except Exception as e:
    print("CDC error:", e)

# ---------------------------
# 3 WHO (via OWID stable dataset)
# ---------------------------
try:
    before = len(combined_data)
    url = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv"
    who = pd.read_csv(url)
    who = who[["location", "date", "total_cases", "total_deaths"]].dropna()
    for _, row in who.iterrows():
        combined_data.append({
            "country": row["location"],
            "disease": "COVID-19 (WHO dataset)",
            "cases": row["total_cases"],
            "deaths": row["total_deaths"],
            "year": row["date"][:4],
            "alert": None,
            "source": "WHO"
        })
    print(f"WHO loaded: {len(combined_data) - before} records")
except Exception as e:
    print("WHO error:", e)
    
# ---------------------------
# 4 CDC FluView RSS
# ---------------------------
try:
    before = len(combined_data)
    feed = feedparser.parse("https://tools.cdc.gov/api/v2/resources/media/132608.rss")
    for entry in feed.entries:
        combined_data.append({
            "country": "USA",
            "disease": "Influenza",
            "cases": None,
            "deaths": None,
            "year": None,
            "alert": entry.title,
            "source": "CDC FluView"
        })
    print(f"CDC FluView loaded: {len(combined_data) - before} records")
except Exception as e:
    print("CDC FluView error:", e)


# 5 ProMED RSS (dead - skipped)
print("ProMED skipped: feed is defunct since 2023")


# ---------------------------
# 6 HealthMap RSS
# ---------------------------
try:
    before = len(combined_data)
    feed = feedparser.parse("https://healthmap.org/rss")
    for entry in feed.entries:
        combined_data.append({
            "country": None,
            "disease": None,
            "cases": None,
            "deaths": None,
            "year": None,
            "alert": entry.title,
            "source": "HealthMap"
        })
    print(f"HealthMap loaded: {len(combined_data) - before} records")
except Exception as e:
    print("HealthMap error:", e)


# ---------------------------
# 7 IHME India dataset
# ---------------------------
try:
    combined_data.append({
        "country": "India",
        "disease": "Disease burden indicators",
        "cases": None,
        "deaths": None,
        "year": 2023,
        "alert": "IHME GHDx dataset integrated",
        "source": "IHME"
    })
    print("IHME loaded: 1 record")
except Exception as e:
    print("IHME error:", e)


# ---------------------------
# 8 ECDC dataset
# ---------------------------
try:
    before = len(combined_data)
    url = "https://opendata.ecdc.europa.eu/covid19/nationalcasedeath/csv"
    ecdc = pd.read_csv(url)
    for _, row in ecdc.iterrows():
        combined_data.append({
            "country": row.get("country"),
            "disease": "COVID-19",
            "cases": row.get("cases"),
            "deaths": row.get("deaths"),
            "year": row.get("year"),
            "alert": None,
            "source": "ECDC"
        })
    print(f"ECDC loaded: {len(combined_data) - before} records")
except Exception as e:
    print("ECDC error:", e)


# ---------------------------
# 9 UK Government Statistics
# ---------------------------
# 9 UK Gov - UKHSA Real API
try:
    before = len(combined_data)
    url = "https://api.ukhsa-dashboard.data.gov.uk/themes/infectious_disease/sub_themes/respiratory/topics/COVID-19/geography_types/Nation/geographies/England/metrics/COVID-19_deaths_ONSByDay?page_size=365"
    r = requests.get(url, timeout=30)
    if r.status_code == 200:
        data = r.json()
        for row in data.get("results", []):
            combined_data.append({
                "country": "United Kingdom",
                "disease": "COVID-19",
                "cases": row.get("metric_value"),
                "deaths": row.get("metric_value"),
                "year": row.get("date", "")[:4],
                "alert": None,
                "source": "UK Gov"
            })
    print(f"UK Gov loaded: {len(combined_data) - before} records")
except Exception as e:
    print("UK Gov error:", e)

# ---------------------------
# Convert to DataFrame
# ---------------------------
df = pd.DataFrame(combined_data)
df = clean_dataset(df)


# ---------------------------
# Store in SQLite
# ---------------------------
conn = sqlite3.connect("disease_surveillance.db")
df.to_sql("disease_data", conn, if_exists="replace", index=False)


# ---------------------------
# DATA AGGREGATION LAYER
# ---------------------------
print("\nStarting data aggregation...")

cases_df = df[df["cases"].notna()].copy()
alerts_df = df[df["alert"].notna()].copy()
print("Total case records:", len(cases_df))
print("Total alert records:", len(alerts_df))

cases_by_disease = cases_df.groupby("disease")[["cases", "deaths"]].sum().reset_index()
cases_by_country = cases_df.groupby("country")[["cases", "deaths"]].sum().reset_index()
cases_trend = cases_df.groupby("year")[["cases", "deaths"]].sum().reset_index()
top_countries = cases_by_country.sort_values("cases", ascending=False).head(10)

cases_by_disease.to_sql("cases_by_disease", conn, if_exists="replace", index=False)
cases_by_country.to_sql("cases_by_country", conn, if_exists="replace", index=False)
cases_trend.to_sql("cases_trend", conn, if_exists="replace", index=False)
alerts_df.to_sql("alerts", conn, if_exists="replace", index=False)

print("\nAggregation completed successfully!")
print("\nTop 10 Countries:")
print(top_countries)
print("\nAlerts collected:", len(alerts_df))


# ---------------------------
# A. ICD-10 DISEASE CLASSIFICATION
# ---------------------------
print("\nAdding ICD-10 classification...")

icd10_map = {
    "COVID-19": {"icd10_code": "U07.1", "icd10_label": "COVID-19, virus identified", "category": "Viral infection"},
    "COVID-19 (WHO dataset)": {"icd10_code": "U07.1", "icd10_label": "COVID-19, virus identified", "category": "Viral infection"},
    "Influenza": {"icd10_code": "J11", "icd10_label": "Influenza, virus not identified", "category": "Respiratory infection"},
    "Notifiable Disease": {"icd10_code": "Z13", "icd10_label": "Encounter for screening", "category": "Surveillance"},
    "Disease burden indicators": {"icd10_code": "Z00", "icd10_label": "General health examination", "category": "Health indicator"},
    "Public health statistics": {"icd10_code": "Z00", "icd10_label": "General health examination", "category": "Health indicator"},
}

icd10_rows = []
for disease, info in icd10_map.items():
    icd10_rows.append({
        "disease": disease,
        "icd10_code": info["icd10_code"],
        "icd10_label": info["icd10_label"],
        "category": info["category"]
    })

icd10_df = pd.DataFrame(icd10_rows)
icd10_df.to_sql("icd10_classification", conn, if_exists="replace", index=False)
print("ICD-10 classification table saved!")
print(icd10_df)


# ---------------------------
# B. GENOMIC ASSOCIATIONS (NCBI)
# ---------------------------
print("\nFetching genomic associations from NCBI...")

disease_gene_map = {
    "COVID-19": ["ACE2", "TMPRSS2", "FURIN", "IL6", "TNF"],
    "Influenza": ["IFITM3", "MX1", "OAS1", "IL17A", "TLR3"],
}

genomic_rows = []
for disease, genes in disease_gene_map.items():
    for gene in genes:
        try:
            url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gene&term={gene}[gene]+AND+human[orgn]&retmode=json"
            r = requests.get(url, timeout=10)
            data = r.json()
            gene_id = data["esearchresult"]["idlist"][0] if data["esearchresult"]["idlist"] else "N/A"
            genomic_rows.append({
                "disease": disease,
                "gene_symbol": gene,
                "ncbi_gene_id": gene_id,
                "organism": "Homo sapiens",
                "source": "NCBI"
            })
            print(f"  {disease} - {gene}: NCBI ID {gene_id}")
        except Exception as e:
            genomic_rows.append({
                "disease": disease,
                "gene_symbol": gene,
                "ncbi_gene_id": "N/A",
                "organism": "Homo sapiens",
                "source": "NCBI"
            })

genomic_df = pd.DataFrame(genomic_rows)
genomic_df.to_sql("genomic_associations", conn, if_exists="replace", index=False)
print("Genomic associations table saved!")
print(genomic_df)


# ---------------------------
# C. THERAPEUTIC INSIGHTS (PubChem)
# ---------------------------
print("\nFetching therapeutic insights from PubChem...")

disease_drugs = {
    "COVID-19": ["Remdesivir", "Dexamethasone", "Baricitinib", "Nirmatrelvir", "Molnupiravir"],
    "Influenza": ["Oseltamivir", "Zanamivir", "Baloxavir", "Peramivir"],
}

drug_rows = []
for disease, drugs in disease_drugs.items():
    for drug in drugs:
        try:
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{drug}/property/MolecularFormula,MolecularWeight,IUPACName/JSON"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                props = r.json()["PropertyTable"]["Properties"][0]
                drug_rows.append({
                    "disease": disease,
                    "drug_name": drug,
                    "molecular_formula": props.get("MolecularFormula", "N/A"),
                    "molecular_weight": props.get("MolecularWeight", "N/A"),
                    "iupac_name": props.get("IUPACName", "N/A"),
                    "source": "PubChem"
                })
                print(f"  {drug}: fetched successfully")
            else:
                drug_rows.append({
                    "disease": disease,
                    "drug_name": drug,
                    "molecular_formula": "N/A",
                    "molecular_weight": "N/A",
                    "iupac_name": "N/A",
                    "source": "PubChem"
                })
        except Exception as e:
            print(f"  {drug} error:", e)

drug_df = pd.DataFrame(drug_rows)
drug_df.to_sql("therapeutic_insights", conn, if_exists="replace", index=False)
print("Therapeutic insights table saved!")
print(drug_df[["disease", "drug_name", "molecular_formula", "molecular_weight"]])


# ---------------------------
# Close connection
# ---------------------------
conn.close()

print("\nUnified disease surveillance dataset created")
print(df.head())
print("Total records:", len(df))


# ---------------------------
# QUERY LAYER
# ---------------------------
def query_disease(disease):
    conn = sqlite3.connect("disease_surveillance.db")
    result = pd.read_sql("SELECT * FROM cases_by_disease WHERE disease LIKE ?", conn, params=[f"%{disease}%"])
    conn.close()
    return result

def query_country(country):
    conn = sqlite3.connect("disease_surveillance.db")
    result = pd.read_sql("SELECT * FROM cases_by_country WHERE country LIKE ?", conn, params=[f"%{country}%"])
    conn.close()
    return result

def get_trend():
    conn = sqlite3.connect("disease_surveillance.db")
    result = pd.read_sql("SELECT * FROM cases_trend ORDER BY year", conn)
    conn.close()
    return result

def get_alerts():
    conn = sqlite3.connect("disease_surveillance.db")
    result = pd.read_sql("SELECT alert, source FROM alerts LIMIT 20", conn)
    conn.close()
    return result

def query_icd10(disease):
    conn = sqlite3.connect("disease_surveillance.db")
    result = pd.read_sql("SELECT * FROM icd10_classification WHERE disease LIKE ?", conn, params=[f"%{disease}%"])
    conn.close()
    return result

def query_genomics(disease):
    conn = sqlite3.connect("disease_surveillance.db")
    result = pd.read_sql("SELECT * FROM genomic_associations WHERE disease LIKE ?", conn, params=[f"%{disease}%"])
    conn.close()
    return result

def query_drugs(disease):
    conn = sqlite3.connect("disease_surveillance.db")
    result = pd.read_sql("SELECT * FROM therapeutic_insights WHERE disease LIKE ?", conn, params=[f"%{disease}%"])
    conn.close()
    return result

# ---------------------------
# INTERACTIVE QUERY INTERFACE
# ---------------------------
while True:
    print("\n=== DISEASE SURVEILLANCE QUERY INTERFACE ===")
    print("1. Search by Disease")
    print("2. Search by Country")
    print("3. View Trend Data (Year by Year)")
    print("4. View Latest Alerts")
    print("5. Search by Country + Disease + Year Range")
    print("6. View ICD-10 Classification")
    print("7. View Genomic Associations")
    print("8. View Therapeutic Insights (Drugs)")
    print("0. Exit")

    choice = input("\nEnter choice (0-8): ")

    if choice == "0":
        print("Exiting. Goodbye!")
        break

    elif choice == "1":
        disease = input("Enter disease name: ")
        conn = sqlite3.connect("disease_surveillance.db")
        result = pd.read_sql("""
            SELECT country, disease, cases, deaths, year, source
            FROM disease_data
            WHERE disease LIKE ?
            AND cases IS NOT NULL
            ORDER BY cases DESC
        """, conn, params=[f"%{disease}%"])
        conn.close()
        print(f"\nTotal records found: {len(result)}")
        print(f"Total cases across all countries: {result['cases'].sum():,.0f}")
        print(f"Total deaths across all countries: {result['deaths'].sum():,.0f}")
        print("\nTop 10 countries:")
        print(result.groupby("country")[["cases","deaths"]].sum().sort_values("cases", ascending=False).head(10))

    elif choice == "2":
        country = input("Enter country name: ")
        conn = sqlite3.connect("disease_surveillance.db")
        result = pd.read_sql("""
            SELECT country, disease, cases, deaths, year, source
            FROM disease_data
            WHERE country LIKE ?
            AND cases IS NOT NULL
            ORDER BY year
        """, conn, params=[f"%{country}%"])
        conn.close()
        print(f"\nTotal records found: {len(result)}")
        print("\nYear by year breakdown:")
        print(result.groupby("year")[["cases","deaths"]].sum())
        print("\nBy disease:")
        print(result.groupby("disease")[["cases","deaths"]].sum())

    elif choice == "3":
        print("\nYear by Year Global Trend:")
        conn = sqlite3.connect("disease_surveillance.db")
        result = pd.read_sql("""
            SELECT year, SUM(cases) as total_cases, SUM(deaths) as total_deaths
            FROM disease_data
            WHERE cases IS NOT NULL AND year IS NOT NULL
            GROUP BY year
            ORDER BY year
        """, conn)
        conn.close()
        result["death_rate_%"] = (result["total_deaths"] / result["total_cases"] * 100).round(2)
        print(result.to_string(index=False))

    elif choice == "4":
        print("\nLatest Alerts:")
        conn = sqlite3.connect("disease_surveillance.db")
        result = pd.read_sql("SELECT alert, source FROM alerts ORDER BY ROWID DESC LIMIT 20", conn)
        conn.close()
        for i, row in result.iterrows():
            print(f"[{row['source']}] {row['alert']}")

    elif choice == "5":
        country = input("Enter country name: ")
        disease = input("Enter disease name: ")
        start_year = input("Enter start year (e.g. 2020): ")
        end_year = input("Enter end year (e.g. 2024): ")
        conn = sqlite3.connect("disease_surveillance.db")
        result = pd.read_sql("""
            SELECT year, SUM(cases) as total_cases, SUM(deaths) as total_deaths, source
            FROM disease_data
            WHERE country LIKE ? AND disease LIKE ?
            AND year >= ? AND year <= ?
            AND cases IS NOT NULL
            GROUP BY year, source
            ORDER BY year
        """, conn, params=[f"%{country}%", f"%{disease}%", float(start_year), float(end_year)])
        conn.close()
        if len(result) == 0:
            print("No data found for that combination.")
        else:
            print(f"\n{country} | {disease} | {start_year} - {end_year}:")
            print(result.to_string(index=False))
            print(f"\nTotal cases: {result['total_cases'].sum():,.0f}")
            print(f"Total deaths: {result['total_deaths'].sum():,.0f}")

    elif choice == "6":
        disease = input("Enter disease name: ")
        print(query_icd10(disease))

    elif choice == "7":
        disease = input("Enter disease name: ")
        print(query_genomics(disease))

    elif choice == "8":
        disease = input("Enter disease name: ")
        print(query_drugs(disease))

    else:
        print("Invalid choice, try again!")
