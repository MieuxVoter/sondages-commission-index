import marimo

__generated_with = "0.16.2"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import pandas as pd
    import requests
    from bs4 import BeautifulSoup

    # from playwright.sync_api import sync_playwright

    from datetime import datetime

    base = "https://www.commission-des-sondages.fr/notices/medias/dossiers/view"

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
        # 'Accept': '*/*',
        # "Accept-Encoding": "gzip, deflate, br, zstd"
    }


@app.cell
def _():
    current_year = datetime.now().year
    return (current_year,)


@app.cell
def _(current_year):
    current_year
    return


@app.function
def list_year(year):
    url = f"{base}/{year}"

    s = requests.Session()
    s.get("https://www.commission-des-sondages.fr/notices/")
    # url = "https://www.commission-des-sondages.fr/notices/medias/dossiers/view/2025" #.replace("2016", "2025")
    page = s.get(url, headers=headers)
    # print(url)
    # print(page)
    # print(page.text)
    html = BeautifulSoup(page.text, "html.parser")

    # with sync_playwright() as p:
    #     browser = p.firefox.launch(headless=True)  # Change to True for headless mode
    #     page = browser.new_page()
    #     page.goto("https://www.commission-des-sondages.fr/notices/")
    #     page.wait_for_timeout(1000)
    #     page.goto(url)
    #     #page.wait_for_timeout(10000)
    #     html = BeautifulSoup(page.content(), "html.parser")
    #     #print(html)
    #     browser.close()

    pdf = html.find_all("a", {"class": "pdf_download"})

    # print([ { "name": a.text, "url": a['href'] } for a in pdf ])

    return [{"name": a.text, "href": a["href"]} for a in pdf]


@app.cell
def _():
    list_year(2025)
    return


@app.cell
def _(current_year):
    # Election category constants
    PRES = "Pres"
    PRIM = "Prim"
    MUN = "Mun"
    LEG = "Leg"

    # Keyword patterns for categorization
    PRIMARY_KEYWORDS = [
        "prim d",
        "prim g",  # Check these first (more specific)
        "primd",
        "primg",
        "prims",
        "primaire",
        "prim",
    ]

    PRESIDENTIAL_KEYWORDS = ["pres", "présidentielle", "presidentielle"]

    MUNICIPAL_KEYWORDS = ["mun", "municipal", "municipale"]

    LEGISLATIVE_KEYWORDS = ["leg", "législative", "legislative", "legisl"]

    def categorize_election(name):
        """
        Categorize election type based on keywords in the name.
        Returns: 'Pres' for presidential, 'Prim' for primaries,
                 'Mun' for municipal, 'Leg' for legislative
        """
        name_lower = name.lower()

        # Check for primaries FIRST (more specific than presidential)
        if any(keyword in name_lower for keyword in PRIMARY_KEYWORDS):
            return PRIM

        # Check for presidential elections
        if any(keyword in name_lower for keyword in PRESIDENTIAL_KEYWORDS):
            return PRES

        # Check for municipal elections
        if any(keyword in name_lower for keyword in MUNICIPAL_KEYWORDS):
            return MUN

        # Check for legislative elections
        if any(keyword in name_lower for keyword in LEGISLATIVE_KEYWORDS):
            return LEG

        # Default to None if no match
        return None

    index = pd.concat(
        [
            pd.DataFrame.from_records(list_year(year)).assign(year=year).iloc[::-1]
            for year in range(2016, current_year + 1)
        ]
    ).assign(categorie=lambda df: df["name"].apply(categorize_election))
    return (index,)


@app.cell
def _(index):
    print(len(index))
    return


@app.cell
def _(index):
    index_sorted = index.assign(
        id=lambda df: (
            df.name.str.strip()
            .str.replace(" ", "-")
            .str.split("-")
            .apply(lambda x: x[0])
            # .astype('int')
        )
    ).sort_values("id")
    return (index_sorted,)


@app.cell
def _(index_sorted):
    index_sorted
    return


@app.cell
def _(index_sorted):
    index_sorted.query("id.duplicated()")
    return


@app.cell
def _(index_sorted):
    index_sorted.query("id.str.contains('-')")
    return


@app.cell
def _(index):
    index.to_csv("base.csv", index=False)
    return


if __name__ == "__main__":
    app.run()
