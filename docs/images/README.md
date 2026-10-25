# Provenance des visuels

La présentation utilise les couleurs, les textes et les captures de Meloo. La structure de la page
s’inspire de [Tangerine](https://tangerineformac.com/) : geste principal, exemples, formats et traitement local.
Aucun visuel ni texte promotionnel de ce site n’est reproduit.

- `atelier-orange.png`, `atelier-melina.png`, `roue-orange.png`, `roue-melina.png`, `reglages-melina.png`,
  `fonctionnalites.png` et `conversion-webp.png` : vrais widgets de Meloo rendus hors écran par
  `scripts/capture_documentation.py`, avec un profil isolé et le fichier de démonstration du dépôt.
- `meloo-beta.png` : composition de présentation réalisée avec ces rendus de la roue.
- `geste-ctrl.svg` : schéma original expliquant les trois étapes.
- `menu-icone-windows.png` et `formats-configurables.png` : captures d’utilisation fournies par l’utilisateur.
- `depot-word-demo.png`, `depot-powerpoint-demo.png` et `roue-melina-bureau-demo.png` : illustrations issues
  de trois captures fournies par l’utilisateur, retouchées avec l’outil intégré **imagegen** pour remplacer
  les aperçus de documents par une démo. Elles ne sont pas des captures brutes ; leur rendu peut légèrement varier.
  Les captures originales contenant les documents ne sont pas incluses dans le dépôt.

Les captures rendues hors écran ne prouvent pas le fonctionnement du geste dans l’Explorateur.
Les résultats de validation de la publication sont disponibles séparément dans `VALIDATION.json`.

## Consigne de retouche

Le même prompt a été appliqué séparément aux trois captures de glissement, chacune étant la seule image cible.

```text
Use case: precise-object-edit. Edit target: attached Windows Meloo screenshot. Purpose: safely publish this real application screenshot in a French README. Change ONLY the contents of the small floating white document thumbnail: erase its entire original document content, text, tables and orange reader logo, replacing with an opaque plain white fictional demo document containing only the large centered words "DOCUMENT" and "DÉMO" and a few simple neutral gray lines. Absolutely no trace of the old thumbnail content must remain. Keep the thumbnail at the exact same size and position, and keep the entire rest of the screenshot unchanged: dark desktop background, circular menu geometry, colors, UI text, highlighted sector, plus Copier badge where present. Do not redesign, relabel, translate, move, crop or add UI. Preserve original image aspect ratio and composition. No additional branding, watermark or labels.
```
