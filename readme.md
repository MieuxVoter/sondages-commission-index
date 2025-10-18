# NSPPolls · commission des sondages

Ce dépôt contient :

 - le code sous forme de scripts Python pour produire des données à partir du site de [la commission des sondages]
 - les données sous forme de catalogue unifié
 - les archives PDF des notices de sondages

L'actualité des sondages n'étant pas actuellement suractive, les scripts sont éxécutés tous les matins à `06:00 UTC` (Paris : `08:00` heure d'été, `07:00` d'hiver).

Le dépôt vit principalement sur [codeberg] mais est également dupliqué automatiquement sur [github]. Toutes les interactions sur github seront poliment ignorées, venez sur codeberg ☺️.

[la commission des sondages]: https://www.commission-des-sondages.fr/
[codeberg]: https://codeberg.org/nsppolls/sondages-commission-index
[github]: https://github.com/nsppolls/sondages-commission-index


## données et flux

|         fichier           |  contenu                  |
|--------------------|--------------------|
| [`notices_catalog.csv`]   | **Catalogue unifié** de tous les sondages avec catégorisation, liens et chemins locaux vers les PDFs |
| [`base.csv`]              | Liste brute des sondages référencés sur le site de la commission (généré par scrap.py) |
| [`files.csv`]             | Liste des fichiers PDF téléchargés avec métadonnées (généré par download.py) |
| [`sondages-commission-index.rss`]| Tous les changements sur ce dépôt en attendant un fil RSS comme il faut |

[`notices_catalog.csv`]: https://codeberg.org/nsppolls/sondages-commission-index/src/branch/main/notices_catalog.csv
[`base.csv`]: https://codeberg.org/nsppolls/sondages-commission-index/src/branch/main/base.csv
[`files.csv`]: https://codeberg.org/nsppolls/sondages-commission-index/src/branch/main/files.csv
[`sondages-commission-index.rss`]: https://codeberg.org/nsppolls/sondages-commission-index.rss

### Catégories de sondages

Les sondages sont automatiquement catégorisés selon leur type :

- **Pres** : Élections présidentielles
- **Prim** : Élections primaires (tous partis)
- **Mun** : Élections municipales
- **Leg** : Élections législatives

## scripts

|          script          |  contenu                  |
|--------------------|--------------------|
| [`scripts/scrap.py`]      | Scrape le site de la commission et produit `base.csv` avec catégorisation automatique |
| [`scripts/download.py`]   | Télécharge les PDFs manquants de façon incrémentale et produit `files.csv` |
| [`scripts/merge_files.py`]| **Fusionne** `base.csv` et `files.csv` en un catalogue unifié `notices_catalog.csv` |
| [`scripts/export_pdfs.py`]| Exporte les PDFs filtrés par catégorie et période vers un répertoire |

[`scripts/scrap.py`]: https://codeberg.org/nsppolls/sondages-commission-index/src/branch/main/scripts/scrap.py
[`scripts/download.py`]: https://codeberg.org/nsppolls/sondages-commission-index/src/branch/main/scripts/download.py
[`scripts/merge_files.py`]: https://codeberg.org/nsppolls/sondages-commission-index/src/branch/main/scripts/merge_files.py
[`scripts/export_pdfs.py`]: https://codeberg.org/nsppolls/sondages-commission-index/src/branch/main/scripts/export_pdfs.py

### Utilisation des scripts

```bash
# Flux complet de mise à jour
python scripts/scrap.py           # Scrape et catégorise
python scripts/download.py        # Télécharge les nouveaux PDFs
python scripts/merge_files.py     # Crée le catalogue unifié

# Export sélectif de PDFs
python scripts/export_pdfs.py --category Pres --output exported_pdfs
python scripts/export_pdfs.py --category Prim --after 2022-01-01
python scripts/export_pdfs.py --dry-run  # Voir ce qui serait exporté
```

## automatisation

|  action                  |          récurrence          | description |
|--------------------|--------------------|---|
| [update_notices.yml]     | Tous les matins à `06:00 UTC` | Scrape l'index, télécharge les nouveaux PDFs, fusionne les données et commit les changements |

[update_notices.yml]: https://github.com/nsppolls/sondages-commission-index/blob/main/.github/workflows/update_notices.yml

Le workflow GitHub Actions exécute automatiquement :
1. `scrap.py` - Récupération et catégorisation
2. `download.py` - Téléchargement incrémental
3. `merge_files.py` - Création du catalogue unifié
4. Commit automatique si des changements sont détectés

## structure du projet

```
.
├── notices_catalog.csv          # Catalogue unifié (fichier principal)
├── base.csv                     # Données brutes du scraping
├── files.csv                    # Métadonnées des PDFs téléchargés
├── archives/                    # PDFs organisés par année/mois
│   ├── 2016/
│   ├── 2017/
│   └── ...
├── extracted_texts/             # Textes extraits des PDFs présidentiels
├── scripts/
│   ├── scrap.py                # Scraping avec catégorisation
│   ├── download.py             # Téléchargement incrémental
│   ├── merge_files.py          # Fusion en catalogue
│   ├── export_pdfs.py          # Export sélectif
│   └── requirements.txt        # Dépendances Python
└── .github/
    └── workflows/
        └── update_notices.yml  # Automatisation quotidienne
```

## voir aussi

- [Liste de sondages sur l'élection présidentielle française de 2027](https://fr.wikipedia.org/wiki/Liste_de_sondages_sur_l%27%C3%A9lection_pr%C3%A9sidentielle_fran%C3%A7aise_de_2027) · Wikipédia en Français
