# Licences, provenance et sources tierces

Le code propre à Meloo est sous AGPL-3.0-or-later. Les parties adaptées et les moteurs
conservent leurs licences : les textes de `licenses/` et les notices livrées par les
composants font foi. L’application n’est pas proposée comme un ensemble entièrement MIT.

## Code de la roue

La géométrie de `zeste/radial.py` adapte `NativeApp/Sources/Radial/RadialView.swift`
d’Open-Tangerine, révision `a1ff18575c5000cc50373e851e2bbe7a2b919245`, GPL-3.0-only.
Les crédits Open-Tangerine, Satsuma (MIT) et DragShift (MIT) sont conservés dans `licenses/`.
Les adaptations Python/Qt sont identifiées dans l’en-tête du fichier.
La combinaison GPLv3/AGPLv3 conserve la licence de chaque partie, conformément à leurs clauses de combinaison.

## Moteurs distribués

| Composant | Version de référence | Sources et construction |
| --- | --- | --- |
| Python | 3.12.10 | Archive officielle CPython ; licence PSF et notices associées |
| Qt / PySide / Shiboken | 6.12.0 | Archives officielles Qt et PySide, incluant scripts et composants tiers ; LGPLv3/GPLv3 selon module |
| PyMuPDF / MuPDF | PyMuPDF 2.0 | Source PyPI et moteur MuPDF référencé par son script de construction ; AGPLv3 / option commerciale non acquise |
| FFmpeg | 7.1, Gyan essentials | Source FFmpeg `b08d7969c5`, configuration conservée dans `licenses/FFmpeg-build-license.txt`, recette d’assemblage dans les sources imageio-ffmpeg 0.6.0 ; GPLv3+ |
| Pandoc | 3.9 | Source officielle avec fichiers Cabal/Stack et workflow de compilation ; GPLv2 ou ultérieure |
| LibreOffice | 26.8.1.1 | Sources core, dictionnaires, aide et traductions ; dépendances et recettes `external/` dans core ; MPL/LGPL et licences des composants |
| Volet de partage Windows | C# / .NET 9 | Code dans `native/Share`, reconstruction décrite dans BUILD.md ; runtime .NET sous MIT et notices associées |
| Autres bibliothèques Python | Versions fixées | Sources PyPI, textes de licences et recettes de construction propres à chaque paquet |

Les index [source-catalog.json](../licenses/source-catalog.json) et
[native-source-catalog.json](../licenses/native-source-catalog.json) recensent les URL,
versions, tailles et SHA-256 obtenus pendant la préparation. Les archives miroir sont
jointes à la [version GitHub](https://github.com/bhuit/Meloo/releases/tag/v0.4.2).
Les sources de Meloo comprennent aussi les scripts et images de l’assistant Inno Setup.

Les moteurs sont repris sans modification. Les DLL Qt restent séparées et remplaçables
par une version compatible ; aucune interdiction de modification, reconstruction,
débogage ou rétro-ingénierie pour exercer les droits LGPL n’est ajoutée.

## Périmètre des vérifications

L’inventaire `licenses/python-environment/inventory.json` décrit l’environnement de
construction historique, plus large que le programme livré. Les exclusions explicites
figurent dans `build_portable.py`. Un paquet recensé ne signifie pas qu’il est embarqué.

Une archive du wrapper Python ne remplace pas les sources de ses bibliothèques natives.
Les archives officielles et recettes sont fournies comme références de reconstruction ;
la compilation bit à bit de tous les moteurs tiers n’a pas été vérifiée. En particulier,
la configuration FFmpeg identifie les bibliothèques activées, mais ne constitue pas à elle
seule un inventaire des révisions de chacune des bibliothèques externes du build Gyan.
Ce dossier ne vaut pas certification juridique exhaustive, ni validation des brevets
éventuellement applicables aux codecs ou de la disponibilité du nom Meloo comme marque.

## Vie privée et mentions de droits

Les journaux locaux, profils utilisateurs, historiques, identifiants et chemins de la
machine de développement sont exclus du dépôt et des archives de sources publiques.
Les noms et contacts publics des auteurs dans les licences tierces sont conservés.
Les commits utilisent le pseudonyme GitHub du mainteneur et une adresse GitHub noreply.

Le nettoyage PDF conserve les champs de logiciel (`Producer`, `Creator`) et les notices
XMP de droits standard. Cette opération ne supprime pas les noms éventuels des titulaires
de droits et ne garantit pas l’anonymisation des pages, pièces jointes ou champs non standard.
