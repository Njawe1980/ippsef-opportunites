# Opportunités IPPSEF — collecte du lundi

Collecteur autonome sans dépendance payante. Il extrait uniquement les titres, organismes, lieux disponibles, dates limites et liens des annonces publiques pertinentes pour l’éducation, les compétences et la recherche. Les descriptions intégrales ne sont pas redistribuées.

## Fonctionnement
- Exécution chaque lundi à 06 h UTC (06 h à Dakar), avec les éventuels retards de GitHub Actions.
- Dépôt public requis : le workflow refuse de fonctionner dans un dépôt privé.
- Runner standard ubuntu-latest, maximum 10 minutes. Aucun runner payant, API payante, modèle IA, cache ou artefact stocké.
- Les données JSON sont servies depuis le dépôt public. Aucune republication hebdomadaire sur Netlify.
- Respect de robots.txt et des erreurs d’accès. Aucune authentification sur les sources.
- Les offres sans échéance explicite ou déjà expirées sont exclues.
- En cas d’échec d’une source, ses offres précédentes sont conservées au maximum sept jours et seulement jusqu’à leur échéance. Les statuts exposent les échecs.
- Les résultats sont une sélection, et non un inventaire exhaustif. Les candidatures se font sur les sites sources.

## Vérification locale
```sh
python -m unittest discover -s tests
python scripts/collect_opportunities.py
```

Le champ automation_active reste faux pour les essais locaux. Seul le workflow activé le positionne à vrai. La connexion au site doit être faite après validation d’une première exécution GitHub.

## Gratuité
Les runners standard GitHub Actions sont gratuits pour les dépôts publics : https://docs.github.com/en/billing/concepts/product-billing/github-actions
Les frais déjà existants du domaine et de l’hébergement du site restent indépendants. Ce collecteur n’ajoute aucun abonnement. Les conditions des services peuvent évoluer ; aucun passage automatique à une offre payante n’est prévu.

## Contenu public
Ce dépôt contient uniquement le nouveau collecteur, ses tests, la configuration des sources et les métadonnées publiques. Il ne contient ni les fichiers privés du site, ni des clés, ni des identifiants, ni des candidatures.
