MELOO 0.4.1 — ROUE ORGANISÉE

Créer ZIP reste en haut pour tout fichier ou dossier, même une sélection mixte ou une archive existante. Les fichiers sont stockés tels quels. Les conversions gardent des positions fixes par famille ; le format actuel reste grisé. Autres formats : survoler ce secteur un instant puis viser la destination. Le centre ne change plus de menu au survol ; Tab passe à Outils puis Actions, ou cliquer sur le centre hors glissement.

MELOO 0.4.0 — NOUVEAU NOM DE ZESTE

Dans Réglages, le switch Orange / Melina applique immédiatement le thème à la roue, aux fenêtres, aux menus et à l’icône de notification. Melina utilise une palette claire rose pastèque et vert menthe ; Orange retrouve son réglage sombre/clair précédent. Le choix est enregistré pour les lancements suivants.

Lancer Meloo.exe. Zeste.exe reste un point d’entrée compatible avec les anciens raccourcis. Le profil de préférences, l’historique, les fonctionnalités et le geste Ctrl restent inchangés.

ZESTE POUR WINDOWS — VERSION 0.3.2
Convertir, modifier et organiser des fichiers localement.
Atelier en verre sombre : fichiers à gauche, roue au centre, résultats à droite.
Déplace la roue flottante en maintenant le bouton gauche sur son centre.

DÉMARRER

Dans ce projet : double-cliquer sur Lancer-Zeste.cmd.
Dans la distribution portable : ouvrir Zeste.exe dans le dossier Zeste extrait.
Pour l’archive ZIP : choisir « Extraire tout » avant d’ouvrir Zeste.exe.
Zeste démarre en arrière-plan : son icône orange apparaît dans la zone de
notification, en bas à droite (ou sous la flèche des icônes masquées de Windows).
Clic droit sur l’icône : roue, réglages, fonctionnalités, atelier, résultats ou quitter.
Conserver le dossier Zeste entier : _internal et tools contiennent les moteurs.
Python, un compte Apple, un abonnement et une connexion Internet ne sont pas
nécessaires pour utiliser le portable préparé.

1. Dans l’Explorateur ou sur le Bureau, commencer à glisser un fichier.
2. Pendant le glissement, appuyer sur Ctrl (gauche ou droite).
3. Relâcher Ctrl si souhaité, continuer le glissement, puis déposer sur un secteur.
   Compresser lance directement le mode automatique ; un format lance la conversion.
4. La roue disparaît ; les fichiers sont créés à côté des originaux avec un nom
   distinct. Aucun atelier ni panneau de résultats ne s’ouvre automatiquement.
Double-cliquer sur l’icône affiche seulement la roue. L’atelier avancé reste
accessible explicitement par le menu de l’icône ou avec Zeste.exe --window.

ROUE FLOTTANTE ET RACCOURCIS

Maintenir le bouton gauche au centre de la roue pour la déplacer. Un clic
simple au centre change de menu ; le déplacement ne lance aucune opération.

- Ctrl pendant le glissement : roue avec Compresser et les formats.
- Le relâchement de Ctrl laisse la roue ouverte jusqu’au dépôt ou à l’annulation.
- Pour régler le poids cible : Tab pour afficher Outils, puis déposer sur Compresser.
- Tab change de roue ; Échap ferme ; F8 ouvre la roue depuis l’atelier.
- Le survol du centre conserve la roue actuelle. Tab passe à Outils,
  puis Actions et Convertir. Le secteur Autres formats change de page après un court survol.
- Flèches puis Entrée permettent une sélection au clavier.
- Maintenir le pointeur sur « Suite » pendant le glissement passe à la page suivante.
- Ctrl+O ajoute des fichiers ; Suppr retire la sélection de la liste.
- Ctrl+Q quitte l’application. Le menu de l’icône de notification permet aussi
  de quitter, de rouvrir l’atelier, la roue ou les derniers résultats.
- AltGr n’est pas un raccourci de Zeste.

La version 0.3.2 reçoit les événements souris/Ctrl de Windows en arrière-plan
(Raw Input). Elle conserve uniquement les boutons et touches de commande de la
roue, sans enregistrer le texte saisi ni bloquer les raccourcis des autres apps.

Le déclenchement global est limité à l’Explorateur Windows et au Bureau.
La roue s’ouvre sur le pointeur ; il faut ensuite déplacer le fichier jusqu’au
secteur choisi. Les sorties du panneau peuvent être glissées vers un dossier.

FONCTIONS DISPONIBLES

Images : PNG, JPEG, WebP, AVIF, HEIC/HEIF, TIFF, BMP, GIF et PDF ; lecture SVG.
Outils : compression, dimensions, rotation, collage, images vers PDF, métadonnées,
suppression des métadonnées, lecture QR. Quatre entrées ouvrent l’éditeur :
Retoucher, Annoter, Recadrer, Masquer. Réglages avec aperçu : exposition,
luminosité, contraste, ombres, hautes lumières, saturation, température, teinte,
netteté, clarté, voile, bruit et grain. Annotations : texte, flèches, formes,
numéros, dessin et surlignage. Recadrage par tracé, dimensions ou proportions.
Masques noirs et flous manuels ; export PNG aplati dans une nouvelle copie.
Fond uni ou image avec flou, marge, coins arrondis et ombre. Collage : colonnes,
taille des cases, espacement, coins et fond. Les GIF et TIFF animés/multipages sont traités comme une première image
par les conversions photo ; l’outil de fond refuse les images multipages.

Vidéo : MP4, MOV, MKV, WebM, AVI, WMV ; GIF et extraction du son en MP3/WAV.
Outils : compression, coupe temporelle, recadrage, vitesse, segments, assemblage,
captures à plusieurs positions, retrait du son, masque noir ou flou sur un intervalle,
métadonnées. Le masque et le recadrage vidéo utilisent des coordonnées en pixels.
Le masquage produit un MP4 et conserve la première vidéo et le premier audio.

Audio : MP3, M4A, WAV, FLAC, Ogg, Opus, AIFF, WMA.
Outils : compression, coupe, normalisation, bip sur un intervalle, mono/stéréo,
vitesse, segments, assemblage, métadonnées, visualiseur d’onde exporté en MP4.
Réglages du niveau cible, crête et plage dynamique ; gains gauche/droite ;
dimensions et couleurs du visualiseur. Ordre des assemblages modifiable.

PDF : extraction du texte en TXT/Markdown/HTML/EPUB, images par page, DOCX,
PowerPoint et tableaux Excel ; fusion, séparation, ordre/sélection des pages,
organisation par vignettes avec glisser, duplication, retrait et rotation des pages,
optimisation sans perte, suppression du texte recherché dans une copie,
lecture/édition/nettoyage des métadonnées.
La compression ne publie une copie que si elle est plus petite. Pour un PDF déjà
optimisé, l’original est conservé et aucun nouveau fichier n’est créé.
Le dépôt rapide vers PPTX, PNG et JPG démarre directement sans confirmation.
Un diagnostic reste accessible au survol/clic droit de l’icône de notification,
y compris lorsque le panneau de résultats est désactivé.

Documents et bureautique : conversions locales via LibreOffice et Pandoc,
notamment DOCX, ODT, RTF, TXT, Markdown, HTML, EPUB et PDF ; XLSX/CSV/TSV/ODS/PDF ;
présentations vers PDF, images et PPTX. LibreOffice est une copie privée intégrée,
sans installation globale ni utilisation du profil Office personnel.

Sous-titres : SRT, VTT, texte.
Tout fichier : compression dans une archive ZIP lorsque le format ne dispose
pas d’un compresseur dédié. Édition intégrée des métadonnées JPEG/TIFF, PNG,
PDF, DOCX/XLSX/PPTX et médias compatibles. Pour les autres formats, une fiche
.metadata.json distincte est créée : les métadonnées internes restent inchangées.
Archives : création/conversion ZIP, TAR, GZ, 7z et extraction. RAR nécessite un
extracteur externe reconnu par rarfile : il n’est pas inclus dans ce portable.

Actions : retrouver dans l’Explorateur, copier les fichiers ou leurs chemins,
dupliquer, générer une empreinte SHA-256, copier/déplacer vers un dossier,
étagère flottante, terminal dans le dossier, volet de partage Windows.
« Déplacer » est la seule action qui déplace les originaux, après choix confirmé.

Les traitements s’exécutent en file. Un échec individuel conserve les résultats
réussis d’un lot et apparaît dans l’historique. Annuler arrête le traitement actif
et vide la file en attente. Les fichiers déjà terminés ne sont pas supprimés.

RÉGLAGES ET DONNÉES

« Fonctionnalités… » dans le menu de l’icône orange (ou le bouton des Réglages)
permet d’activer/désactiver chaque outil, format de conversion et action.
Recherche par nom/type, boutons Tout activer/Tout désactiver. Les réglages sont
persistants et appliqués immédiatement à la roue et à l’atelier.
Les outils apparaissent selon le type et le nombre de fichiers : collage,
fusion PDF et assemblage média nécessitent au moins deux fichiers compatibles.

Choix du dossier de sortie, thème clair/sombre, animations réduites, panneau
flottant, maintien dans la zone de notification et lancement à l’ouverture de
Windows. Le démarrage automatique est désactivé tant que la case n’est pas cochée.
Le panneau flottant est désactivé par défaut dans le mode roue seule.

Préférences et historique : %LOCALAPPDATA%\Zeste\settings.ini.
Si ce dossier ne peut pas être créé : user-data près de l’application.
Les tests utilisent un dossier de configuration séparé. L’historique conserve
100 traitements avec chemins des résultats et diagnostics ; il peut être effacé.
Aucune télémétrie ni téléversement de fichiers n’est ajouté par Zeste.
Le bouton Partager ouvre Windows ; l’utilisateur choisit lui-même la destination.

LIMITES DE CETTE VERSION

- Il s’agit d’une reconstruction Windows indépendante, pas d’une exécution du Mac.
  La roue claire reprend l’orange #FF5200 et les dégradés alpha du site officiel.
  Les niveaux alpha sont reproduits ; le flou natif et la réfraction du verre
  macOS ne sont pas identiques dans le compositeur Qt/Windows.
- Le geste global Ctrl+glisser a été confirmé par l’utilisateur en version 0.2.3.
  Les nouveaux outils sont vérifiés par traitements réels et événements Qt.
- Les outils vidéo/audio utilisent des réglages numériques ; pas de lecteur
  avec timeline intégrée. Le masquage des images est manuel, sans détection
  automatique des visages/du texte ni loupe d’annotation. L’éditeur photo
  utilise des filtres locaux propres à Zeste, pas les algorithmes du Mac.
- Pas d’OCR, de suppression de fond par IA, d’AirDrop, de format de sortie Pages,
  d’exclusions d’applications ni de roue globale dans toutes les applications.
- PDF vers PowerPoint crée des images de pages. PDF vers Excel ne fonctionne que
  sur les tableaux détectables. La fidélité PDF vers DOCX dépend du document.
- Un poids cible est approximatif ; une copie n’est pas toujours plus légère.
- Aucun ensemble de tests ne prouve la prise en charge de tous les codecs et
  fichiers réels. Un message d’erreur explicite est affiché lorsqu’un moteur refuse.
- Le volet de partage a un test de démarrage ; l’envoi à une application tierce
  n’a pas été effectué. Les associations Windows restent gérées par le système.

INSTALLATION FACULTATIVE

Le portable fonctionne sans installation. Installer-Zeste.ps1 peut copier une
version complète dans le profil utilisateur et créer un raccourci du menu Démarrer.
Exécution depuis PowerShell dans le dossier :
    .\Installer-Zeste.ps1 -WhatIf
    .\Installer-Zeste.ps1
    .\Installer-Zeste.ps1 -DesktopShortcut
Les anciennes versions sont conservées ; aucun démarrage automatique n’est activé.

DÉVELOPPEMENT / RECONSTRUCTION

Python 3.12 x64 et Windows x64 sont la configuration de référence.
    py -3.12 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --progress-bar off -r requirements-dev.txt
    .\.venv\Scripts\python.exe main.py
    .\.venv\Scripts\python.exe -m pytest tests -q
    .\.venv\Scripts\python.exe build_portable.py

Le build attend les moteurs privés dans tools/LibreOffice et tools/share.
Le partage se reconstruit avec .NET 9 et native/Share/Share.csproj. La commande :
    dotnet publish native/Share/Share.csproj -c Release -r win-x64 --self-contained true -o tools/share -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true
La copie LibreOffice provient de l’extraction administrative du MSI officiel
26.8.1 Windows x86-64 ; elle est livrée dans le portable préparé.
SHA-256 du MSI téléchargé :
C6298B10CFA1748BCBEDAD94C62CE771E240E5021BFD6D7A967CD571B04B5312

CLI disponible avec Python, exemple :
    .\.venv\Scripts\python.exe main.py --convert to:webp --output C:\Resultats photo.png
Le portable est un exécutable graphique : ses conversions CLI produisent des
fichiers et un code de sortie, sans console de sortie standard.

RÉFÉRENCES

Code étudié : https://github.com/sintaxerrorpvtltd/Open-Tangerine
Commit : a1ff18575c5000cc50373e851e2bbe7a2b919245
Archive fournie : Open-Tangerine-0.1.10-macOS.zip, analysée sans exécution.
Vidéo : https://www.youtube.com/watch?v=ykAUNww86So
Elle montre la reconstruction de Wispr Flow/Dicto, pas Tangerine : sa méthode
REA a été appliquée, tandis que les fonctions/style proviennent d’Open Tangerine.
Les prompts complets derrière formulaire n’ont pas été récupérés ni inventés.

Voir docs/MISE-A-JOUR-0.3.2.txt, docs/REFERENCE-ET-VALIDATION.txt, licenses/,
NOTICE.txt et les sources.
