# Dataset survey

Candidate datasets for hierarchical (family / genus / species) classification of tree
species from leaf images.

- **Last updated:** 08/10/2026
- Information below comes from the sources linked in each entry. Anything not confirmed
  is explicitly marked as *not verified*.

## 1. Evaluation criteria

A dataset is useful for this project if it can support not only hierarchical tree-species
classification, but also the data-management, annotation, quality-control and model-evaluation
needs of the other TFGs in the project.

A candidate dataset should therefore provide material that can be ingested, curated,
annotated, versioned, exported and reused by different downstream projects.

1. **Leaf images with usable labels:** images should clearly show leaves and include a
   reliable species label. Images of flowers, fruits or whole plants should be identifiable
   and filterable through metadata.

2. **Tree-species relevance:** preference should be given to datasets focused on tree
   species. The geographic origin, collection context and taxonomic coverage should be
   documented.

3. **Hierarchical taxonomy:** the dataset should include enough species per genus and
   genera per family to support classification and evaluation at species, genus and family
   levels.

4. **Annotation and review potential:** images should be suitable for manual validation,
   correction, quality assessment and potential additional labelling, such as leaf side,
   capture conditions, image quality or morphological attributes.

5. **Metadata quality:** each image should retain provenance information, including source,
   author or contributor, license, taxonomic identifier, capture date and location when
   available.

6. **Dataset scale and class distribution:** the number of images, species, genera and
   families should be known. The distribution of images per taxonomic class should be
   documented to support fair evaluation and identification of long-tailed classes.

7. **Image diversity:** the dataset should distinguish, where possible, isolated leaves on
   controlled backgrounds from leaves photographed in natural environments. Variation in
   lighting, resolution, viewpoint, occlusion and image quality is valuable for robust
   evaluation.

8. **Licensing, attribution and redistribution:** usage conditions must be explicit enough
   to determine whether images can be stored, processed, shared, exported or used to train
   and publish models.

9. **Reusability for other TFGs:** the dataset should be exportable in a documented,
   machine-readable format, with stable identifiers and metadata that allow other projects
   to build datasets, benchmarks, annotation tasks or evaluation experiments without
   duplicating the original collection work.

## 2. Summary table

| Dataset             | Size                          | Main advantage                            | Main drawback                                      | License                            |
| ------------------- | ----------------------------- | ----------------------------------------- | -------------------------------------------------- | ---------------------------------- |
| Pl@ntNet-300K       | 306,146 images, 1,081 species | Large, rich hierarchy, per-image metadata | All plant organs, natural backgrounds, long-tailed | Per-image / ambiguous in aggregate |
| PlantCLEF 2024-26   | ~1.4M images, 7,806 species   | Huge, includes genera and families        | Mixed organs, links to original images             | Not verified                       |
| iNaturalist (AWS)   | Millions                      | Very large, GPS and date                  | Noisy, not only leaves                             | Per image / mostly NC              |
| Leafsnap            | 185 species                   | Trees only, lab and field images          | Rulers in lab images, northeastern USA             | Not verified                       |
| Swedish Leaf        | 1,125 images, 15 classes      | Clean, several species per genus          | Small, some classes only at genus level            | No explicit license found          |
| Flavia              | 1,907 images, 32 species      | Classic benchmark                         | Small, easy, plain background                      | Dataset license not explicit       |
| Folio (UCI)         | 637 images, 32 species        | Clear license                             | Not trees                                          | CC BY 4.0                          |
| 100 leaves (UCI)    | 1,600 samples, 100 species    | Clear license                             | Mostly descriptors                                 | CC BY 4.0                          |
| MalayaKew           | Not verified                  | Visually similar classes                  | License not checked                                | Not verified                       |
| Small Mendeley sets | Hundreds of images            | Some focus on venation                    | Tiny, one license each                             | Check each page                    |


## 3. Detailed entries

### 3.1 Pl@ntNet-300K

- **Links:** https://zenodo.org/records/5645731 (v1.1) · https://zenodo.org/records/10419064 (v2) · https://github.com/plantnet/PlantNet-300K (code)
- **Content:** 306,146 images covering 1,081 species (v1.1). Version 2 has 306,087 images
  and 1,000 species, with better image resolution and better species naming.
- **Size:** 31.7 GB (v1.1 archive).
- **Metadata (v2):** species id, observation id, `organ` (leaf, flower, fruit, habit, other),
  author, per-image `license`, and train/val/test split.
- **Advantages:** very large; rich taxonomy; metadata allows filtering by organ and license.
- **Disadvantages:** not only leaves, so it must be filtered by `organ = leaf`; natural
  backgrounds; strong class imbalance and visually similar species.
- **License, to be resolved:**
  - The Zenodo record for v1.1 lists CC BY 4.0.
  - The v2 metadata gives a per-image license: `cc-by-sa`, `cc-by-nc` or `cc-by-nc-sa`.
  - Pl@ntNet documentation says its images are usually CC BY-SA and require crediting the
    author and the platform.
  - The BSD-2-Clause license on GitHub applies to the benchmark **code**, not to the images.
  - **Working assumption:** treat the license as *per image* and filter with the `license`
    column. NC images prevent commercial use of the combined dataset; SA images require
    derivatives to be shared under the same license.
- **Use in this project:** strong candidate if filtered by `organ = leaf` and by license
  before training. It is the best option for a large, realistic leaf dataset with a usable
  hierarchical structure.
- **Related:** Pl@ntNet also publishes validated observations on GBIF
  (https://identify.plantnet.org/open_data). Attribution rules:
  https://my.plantnet.org/doc/references/using-images

### 3.2 PlantCLEF 2024 / 2025 / 2026

- **Links:** https://www.imageclef.org/PlantCLEF2024 · https://www.imageclef.org/node/347
- **Content:** a subset of the Pl@ntNet training data for south-western Europe, 7,806
  species and about 1.4 million images, complemented with GBIF images with trusted labels.
  The overview papers include a statistics table with images, observations, species,
  genera and families.
- **Advantages:** very large; taxonomy up to family is documented; predefined train, val
  and test splits; metadata includes a `gbif_species_id`.
- **Disadvantages:** mixed plant organs; the task is oriented to vegetation plot images;
  the metadata gives links to the original images.
- **License:** *not verified.* Images originate from Pl@ntNet and GBIF, so per-image
  licenses are likely.
- **Use in this project:** potentially useful as a larger expansion set, but only after
  license filtering and taxonomic checks.

### 3.3 iNaturalist open data

- **Links:** https://registry.opendata.aws/inaturalist-open-data · https://help.inaturalist.org/en/support/solutions/articles/151000173511
- **Content:** licensed images of iNaturalist observations, accessible without an AWS account.
- **License:** varies per image. The default photo license is CC BY-NC, and licenses for
  the observation and for the photo are handled separately.
- **GBIF note:** GBIF only accepts content licensed CC BY, CC BY-NC or CC0, so downloading
  through GBIF already excludes the most restrictive licenses.
- **Advantages:** enormous variety, location and date.
- **Disadvantages:** photos are of whole plants and other organs, high noise, mostly NC.
- **Use in this project:** relevant as a broad, noisy source for pretraining or auxiliary
  supervision, but not as a clean leaf-only benchmark without heavy filtering.

### 3.4 Leafsnap

- **Links:** paper https://mlanthology.org/eccv/2012/kumar2012eccv-leafsnap/ · cropped subset (30 species) https://zenodo.org/record/5061352
- **Content:** tree species of the northeastern United States (185). Two sources: "lab"
  images of pressed leaves from the Smithsonian collection and 7,719 "field" images taken
  with mobile devices outdoors.
- **Advantages:** only trees, only leaves, two capture conditions (useful to study domain shift).
- **Disadvantages:** lab images include size and color calibration rulers that can interfere
  with end-to-end training (a Zenodo subset crops them manually); field images have blur,
  shadows and noise; limited geographic scope.
- **License:** *not verified.* The authors ask that their paper is cited when the dataset
  is used. The direct dataset download link still has to be located.
- **Use in this project:** useful for comparing lab vs field conditions after removing
  rulers and filtering out artifacts, but not a primary source unless the licensing is
  confirmed.

### 3.5 Swedish Leaf

- **Link:** https://cvl.isy.liu.se/research/datasets/swedish-leaf
- **Content:** scanned leaves of 15 tree classes, 75 leaves each (1,125 images), on a plain
  background. Created at Linköping University with the Swedish Museum of Natural History
  (Söderkvist, Master's thesis, 2001).
- **Advantages:** clean, well documented; contains several species of the same genus
  (for example *Salix*, *Ulmus*, *Sorbus*), which is useful to test the hierarchy.
- **Disadvantages:** small; some classes are named only at genus level (Acer, Quercus,
  Tilia, Populus), so species-level labels are not available for them.
- **License:** no explicit license found on the page; cite the thesis.
- **Use in this project:** good benchmark for pipeline validation and hierarchy testing, but
  too small to be a primary training source unless rights are clarified.

### 3.6 Flavia

- **Link:** https://flavia.sourceforge.net/
- **Content:** 1,907 leaf images, 32 species, 50 to 77 images per species, scanned or
  photographed on a plain background, leaves without petiole, sampled in the Yangtze
  Delta region (China).
- **Advantages:** classic benchmark, easy to reproduce results.
- **Disadvantages:** small and very easy (accuracies close to 100% are reported in the literature);
  few species per genus is likely, to be checked.
- **License:** the authors ask to cite their paper. The GPL v2 mentioned on the page refers to
  the program; the dataset license was not explicit.
- **Extra:** the `modeldata` R package ships Flavia-derived features (apex, base, shape and
  edge indicators), which may help prototype morphological labels.
- **Use in this project:** useful for quick baseline comparisons, but not for a final dataset
  if no explicit rights are confirmed.

### 3.7 UCI datasets

- **Folio** (https://archive.ics.uci.edu/dataset/338/folio): 20 photos for each of 32
  species, 637 instances, white background. License **CC BY 4.0**. Species include
  eggplant, rose and papaya, so it is **not a tree dataset**.
- **One-hundred plant species leaves** (https://archive.ics.uci.edu/dataset/241): 16 samples
  for each of 100 species, with shape, margin and texture descriptors. License **CC BY 4.0**.
- **Leaf** (https://archive.ics.uci.edu/ml/datasets/leaf): 340 instances, 40 species, extracted
  features only. **Discarded** (no images).

These are acceptable from a licensing standpoint but are not the target domain and therefore
have low practical relevance for tree species classification.

### 3.8 MalayaKew (MK)

- **Link:** https://researchdata.um.edu.my/dataverse/fsktm (DOI 10.22452/RD/ED1RET)
- **Content:** leaves collected at the Royal Botanic Gardens, Kew. Described as challenging
  because different classes look very similar.
- **License:** *not verified.*
- **Use in this project:** potentially useful for difficult intra-genus classification, but it
  cannot be considered until the repository terms are checked.

### 3.9 Small Mendeley Data sets

Examples (each has its own license, to be read on its page):

- https://data.mendeley.com/datasets/x7ykdk9srt (12 tropical species)
- https://data.mendeley.com/datasets/bgmftbm8zt (3 species)
- https://data.mendeley.com/datasets/4y5nxd2pfy (502 images, 13 species, venation focus)

Too small for the hierarchy, but the venation one may help to validate explainability.

A plant-pathology set (4,502 images, 22 categories by species and health state, CC BY 4.0)
was **discarded**: it targets disease detection, not taxonomy.

### 3.10 Not reviewed in detail yet

- ICL leaf dataset (a comparison table lists 220 species and 17,032 images).
- Smithsonian isolated leaf database (343 leaves, 93 species).
- Herbarium datasets (FGVC).
- GBIF occurrences filtered by license.

These remain candidates for later review, especially if the core dataset shortlist is
insufficient for the planned hierarchy or class balance.

## 4. License implications for the combined dataset

- The most restrictive license among the images used defines what can be done with the
  combined dataset.
- **NC** (non-commercial) images prevent a fully open, commercially reusable dataset.
- **SA** (share-alike) images require derivatives to carry the same license.
- **Attribution** is mandatory for CC BY and its variants: keep author, source and license
  for every image.
- Datasets without an explicit license (Swedish Leaf, Flavia, Leafsnap) should **not** be
  redistributed. Use them locally, cite them, and consider asking the authors.
- For this project, the legal risk is not only the dataset itself but also any derived model,
  processed copies or publication assets that may carry the source license forward.

## 5. Proposed shortlist

1. **Pl@ntNet-300K**, filtered by `organ = leaf` and by license (main candidate).
2. **Swedish Leaf**, to validate the pipeline and the hierarchy.
3. **Leafsnap**, to compare lab and field conditions after removing rulers.
4. **PlantCLEF and iNaturalist (via GBIF)** as later expansion, filtering by license.

## 6. Gap analysis

No existing dataset simultaneously provides all of the following:

- A large collection of tree-leaf images with reliable species labels and a documented
  family-genus-species hierarchy.
- Per-image metadata that supports filtering by plant organ, license, source, capture
  conditions and taxonomic level.
- A workflow for reviewing, correcting and validating automatic predictions or existing
  labels.
- Stable image and annotation identifiers that preserve the history of corrections,
  reviews and dataset versions.
- A storage-agnostic and exportable dataset format that can be reused by other TFGs for
  annotation, benchmarking, model training or evaluation.
- Explicit support for managing derived datasets, such as leaf-only subsets, license-filtered
  subsets, balanced subsets or train/validation/test splits, without losing traceability to
  the original images.

Pl@ntNet-300K is the strongest starting point because it is large, taxonomically rich and
includes per-image organ and license metadata. However, it is not a ready-to-use,
leaf-only, validated and versioned dataset: it contains mixed plant organs, natural
backgrounds, class imbalance and heterogeneous licenses. [2]

Smaller datasets such as Swedish Leaf, Leafsnap and Flavia are useful for controlled
experiments, but they do not provide the scale, metadata richness or annotation workflow
required for a reusable platform. [2]

Therefore, the project will create a platform that:

- Ingests existing datasets, beginning with Pl@ntNet-300K.
- Filters and organizes images using taxonomic and license metadata.
- Provides review and correction workflows for predicted or imported labels.
- Preserves image, annotation, user and dataset-version provenance.
- Exports reproducible leaf-image datasets and associated metadata for other TFGs.
- Supports storage backends that can be selected without changing the application logic.   
