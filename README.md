# Meloo pour Windows

Convertir, compresser et organiser ses fichiers depuis une roue flottante.
Meloo reste dans la zone de notification : commencez à glisser un fichier depuis
l’Explorateur, appuyez sur **Ctrl**, puis déposez-le sur une destination.

## Télécharger

Les installateurs sont disponibles dans les [versions GitHub](https://github.com/bhuit/Meloo/releases).
Choisissez le fichier **Meloo-…-Setup-x64.exe**. Le ZIP « Source code » sert au développement.

- Windows 10 ou 11, processeur x64.
- Installation pour l’utilisateur courant, dossier au choix, raccourcis et désinstallation.
- Les moteurs inclus permettent le traitement local sans compte ni connexion Internet.
- Prévoir environ 2,5 Go pour l’installation, en plus des fichiers produits.
- L’installateur n’est pas signé avec un certificat éditeur. Vérifiez son SHA-256 avec le fichier de sommes fourni.

## Utilisation

1. Lancez Meloo : l’icône apparaît près de l’horloge, éventuellement parmi les icônes masquées.
2. Glissez un fichier depuis l’Explorateur ou le Bureau et appuyez sur **Ctrl**.
3. Déposez-le sur un format ou sur **Créer ZIP**, toujours en haut.
4. Les résultats sont enregistrés à côté des originaux, sauf choix différent dans les réglages.

Un clic droit sur l’icône ouvre les réglages, l’atelier et la configuration des fonctionnalités.
Les thèmes **Orange** et **Melina** s’appliquent à l’application entière.
Déplacez la roue par son centre ; **Tab** change de rubrique et **Échap** la ferme.

## Fonctionnalités

| Fichiers | Exemples d’actions |
| --- | --- |
| Images | PNG, JPEG, WebP, AVIF, HEIC, TIFF, BMP, GIF ; retouche, annotation, recadrage, collage, arrière-plan |
| PDF | Compression sans perte, fusion, organisation des pages, extraction et conversions |
| Audio et vidéo | Conversion, compression, coupe, vitesse, assemblage, normalisation audio, captures vidéo |
| Documents | Word, Excel, PowerPoint, OpenDocument, texte et PDF via LibreOffice et Pandoc |
| Tous fichiers | ZIP, empreinte SHA-256, copie, déplacement et partage Windows |

La compression ne garantit pas une réduction de taille pour un fichier déjà optimisé.
PDF → PowerPoint produit des images de pages ; PDF → Excel dépend des tableaux détectables.
Le nettoyage des métadonnées PDF conserve les mentions de logiciel et de droits et n’anonymise pas le contenu.
RAR nécessite un extracteur externe. Pas d’OCR ni de suppression de fond par IA.
Le [guide détaillé](README.txt) décrit les autres fonctions et limites.

## Développement

Voir [la reconstruction et les tests](docs/BUILD.md), les [licences et sources tierces](docs/THIRD_PARTY.md)
et les [changements](CHANGELOG.md). Le module Python garde son nom historique `zeste`.
Les préférences restent dans `%LOCALAPPDATA%\Zeste` pour préserver la compatibilité.

## Licence et crédits

Le code propre à Meloo est sous **GNU AGPL version 3 ou ultérieure** : [LICENSE.txt](LICENSE.txt).
La géométrie de la roue adaptée d’[Open-Tangerine](https://github.com/sintaxerrorpvtltd/Open-Tangerine)
conserve sa licence GPL-3.0-only ; les droits et notices MIT de Satsuma sont conservés.
Voir [NOTICE.txt](NOTICE.txt) et [licenses/](licenses/).

Meloo est un projet indépendant, sans affiliation ni approbation de l’éditeur de Tangerine.
Les noms et marques des composants restent ceux de leurs propriétaires respectifs.

Les fichiers sont traités sur le PC. Meloo n’ajoute ni télémétrie ni téléversement automatique.
Le partage Windows reste une action explicite de l’utilisateur.
