# Label verification: results and analysis

Results of checking the label mappings of Swedish Leaf and Flavia against the GBIF Backbone
Taxonomy, with an analysis of why some entries could not be verified. This is an
experiment log, not a design document: the surveys describe the options, this file records
what the code produced and how to read it.

- **Run date:** 26/10/2026
- **Authority:** GBIF Backbone Taxonomy, queried through the species match API
  (`https://api.gbif.org/v1/species/match`, plants only). The Backbone changes over time, so
  re-running later can give different answers.
- **Code:** `src/leaf_mlops/data/gbif.py`, `scripts/verify_mapping.py`
- **Raw output:** `datasets/<name>/gbif_report.csv`

## 1. How the check decides

Each mapping entry is sent to GBIF as `Genus species` (authorship and cultivar removed) or as
the genus alone for genus-only classes. An entry is marked `verified` only if **all** of this
holds; otherwise it is marked `needs_review` and the failed condition is written in the report.

| Condition | Why it matters |
| --- | --- |
| Match type is `EXACT` and confidence is at least 90 | A fuzzy match could be a different taxon. |
| GBIF status is `ACCEPTED` | A synonym means the dataset uses an outdated name. |
| GBIF rank equals the expected rank (species or genus) | A match at family or class level means no real match. |
| Genus and family returned by GBIF equal the mapping | The hierarchy is what the project needs to be right. |

The check never edits family, genus or species. It only writes `status` and `note`.

## 2. Results

| Dataset | Classes | `verified` | `needs_review` |
| --- | --- | --- | --- |
| Swedish Leaf | 15 | 14 | 1 |
| Flavia | 32 | 28 | 4 |
| **Total** | **47** | **42 (89%)** | **5 (11%)** |

All 47 entries started as `proposed_unverified`: the mapping was drafted by hand and with an
assistant before this check. So about 9 in 10 entries of that draft agree with GBIF in
name, genus and family, and the check found the other five.

## 3. Why five entries were not verified

| Dataset, class | Name in the dataset | What GBIF says | Cause |
| --- | --- | --- | --- |
| Flavia 7 | *Phoebe nanmu* (Oliv.) Gamble | Synonym of *Machilus nanmu* (Oliv.) Hemsl., family Lauraceae | **A** Outdated genus |
| Flavia 27 | *Manglietia fordiana* Oliv. | Synonym of *Magnolia fordiana* (Oliv.) Hu, family Magnoliaceae | **A** Outdated genus |
| Flavia 16 | *Viburnum awabuki* K.Koch | Synonym of *Viburnum odoratissimum* var. *awabuki*; family Viburnaceae (mapping: Adoxaceae) | **A** Outdated name plus family circumscription |
| Flavia 9 | *Cinnamomum japonicum* Sieb. | Two different names with this spelling (see below); no unique match | **B** Ambiguous name |
| Swedish 14 | *Sorbus intermedia* | Only synonyms and doubtful names; accepted taxon is *Scandosorbus* ×*intermedia* (Ehrh.) Sennikov | **B** Ambiguous name plus new genus |

The full GBIF answers were inspected for these five names (the "match" answer with its
alternatives, and a name search), because the one-line message of the report is not enough
to see the cause.

### Cause A: the dataset uses a name that is no longer accepted (3 of 5)

Flavia was published in 2007 and Swedish Leaf in 2001, and plant names are revised
continuously: genera are merged or split, and species move between them. Three Flavia names
are in that situation. In each case GBIF finds the name **exactly** (confidence 100) but
marks it as a synonym and gives the accepted one. The family is unaffected for *Phoebe* and
*Manglietia*; only the genus (and therefore the species name) changes.

*Viburnum awabuki* has two separate effects. First, it is now treated as a variety of
*V. odoratissimum*, so the species level of the hierarchy changes. Second, GBIF places the
genus in Viburnaceae, whereas the mapping followed the Adoxaceae circumscription (the one
used by APG IV, to be confirmed with a second source). This is a disagreement between
classification systems, not a typing error.

**Consequence for the project:** the same leaf can legitimately carry different genus labels
depending on the year of the source. If a dataset says *Phoebe* and another says *Machilus*,
a model would treat them as different genera. This is exactly what the mapping layer is for:
keep the original label, store the accepted name as the canonical one.

### Cause B: the name is ambiguous for GBIF (2 of 5)

For these two names the match API returns only a higher rank (class for *Cinnamomum
japonicum*, family for *Sorbus intermedia*). That is not "the species does not exist": GBIF
knows several candidates and refuses to pick one.

- ***Cinnamomum japonicum*** exists twice in GBIF with different authorship: *C. japonicum*
  Siebold is a synonym of *Hedyotis pedunculata* (a Rubiaceae), while *C. japonicum* Siebold
  ex Nakai is a Lauraceae synonym of *Cinnamomum chekiangense* Nakai. The query had no
  authorship, so the two homonyms tie. The Flavia label includes "Sieb.", but this alone does
  not separate the two. The leaf is a tree of the laurel family, so the Lauraceae reading is
  the plausible one, but a person must decide.
- ***Sorbus intermedia*** appears only as synonyms of different authors
  (Ehrh., Schult., Pers.) and two doubtful entries. The accepted taxon is a hybrid in a
  separate genus (*Scandosorbus* ×*intermedia*), so both the genus and the "species" level
  change.

**Consequence:** the message in the report ("GBIF rank is FAMILY, expected SPECIES") is
technically correct but hides the cause. The check should show the candidates from the
alternatives list.

## 4. Proposed resolution (to be confirmed by a person)

These are proposals from the GBIF data. They are not applied to the mapping files.

| Original label | Proposed canonical name | Family | Note |
| --- | --- | --- | --- |
| *Phoebe nanmu* | *Machilus nanmu* | Lauraceae | Genus change only. |
| *Manglietia fordiana* | *Magnolia fordiana* | Magnoliaceae | Genus change only. |
| *Viburnum awabuki* | *Viburnum odoratissimum* | Viburnaceae (GBIF) or Adoxaceae (APG IV) | Choose one family system and use it for all datasets. |
| *Cinnamomum japonicum* | *Cinnamomum chekiangense* | Lauraceae | Only if the leaf images match the Lauraceae homonym. |
| *Sorbus intermedia* | *Scandosorbus* ×*intermedia* | Rosaceae | Hybrid; a genus-level label (*Sorbus*) may be safer. |

The original label stays in `original`, so nothing about the source is lost.

## 5. What "verified" does and does not mean

- **It means:** GBIF returns the same accepted name and the same genus and family as the
  mapping, at the time of the run.
- **It does not mean** that the dataset's own label was interpreted correctly. Three
  entries were verified after a spelling correction made in the mapping: Swedish 11
  (*sinerea* read as *Salix cinerea*), Swedish 15 (*silvatica* read as *Fagus sylvatica*) and
  Flavia 25 (*Tonna* read as *Toona sinensis*). GBIF confirming the corrected name is good
  evidence, but not proof that the authors meant that species.
- **It does not mean consensus between authorities.** Swedish 1 (*Ulmus carpinifolia*) is
  accepted by GBIF, but the mapping note warned that other sources may treat it as a synonym
  of *Ulmus minor*. Flavia 29 (*Mahonia bealei*) is accepted as *Mahonia* by GBIF, although
  *Mahonia* is often merged into *Berberis* elsewhere, and Flavia also contains a *Berberis*
  (class 3).
- Six verified entries still carry notes that say "check" or "confirm" (Swedish 1, 2, 11, 13,
  15 and Flavia 29). The status was updated but the manual note was kept on purpose, so they need a
  human to close them.

## 6. Overlap between the two datasets

Overlap decides which cross-dataset experiments are possible.

| Level | Shared between Swedish Leaf and Flavia |
| --- | --- |
| Species | none |
| Genus | *Acer*, *Populus* |
| Family | Rosaceae, Salicaceae, Sapindaceae |

In both shared genera the Swedish Leaf class is genus-only (classes 2 and 12 have no
species), so comparison can only happen at genus level. A species-level experiment between
these two datasets is not possible; a third dataset with overlapping species is needed. Which one
to add is decided by the gap it closes, as described in section 5 of the
[dataset survey](dataset_survey.md).

**Check with the images.** The table above comes from the mappings. After downloading the 13
missing Swedish Leaf classes (so all 15 are present, 1,125 scans), the combined table of images
gives the same result: no shared species, and the genera *Acer* (Flavia 109, Swedish Leaf 75
images) and *Populus* (Flavia 64, Swedish Leaf 150: 75 of *Populus tremula* and 75 labelled only
as *Populus*). An earlier run, made when only 2 of the 15 classes were present, had reported just
*Acer*; that figure was an effect of the incomplete download, not of the data.

The complete combined dataset has 3,032 images, 25 families, 37 genera, 43 species and 4
genus-only classes. Among its 47 classes the images per class go from 50 to 77 (ratio 1.54), so
no class is small.

### 6.1 Identical files inside Swedish Leaf

Once every image had a SHA-256, the integrity part of the report found **3 groups of files with
identical content under different identifiers**, all in class 8 (*Populus tremula*):

| Files | Size (pixels) |
| --- | --- |
| `l8nr016` and `l8nr017` | 854 x 1279 |
| `l8nr031` and `l8nr032` | 1093 x 1805 |
| `l8nr070` and `l8nr071` | 1118 x 1455 |

They are consecutive numbers of the same class with the same size and the same bytes, so the source
stores the same scan twice. Each archive member is written independently by the extraction code, so
this is a property of the source and not of the download.

Why it matters: with a random train/test split, one copy can land in training and the other in the
test set, which inflates the test accuracy. Here it affects 3 of the 75 images of one class (4%),
which is small, but the same effect can be large in bigger sources that contain re-uploaded photos.

What the project does about it: the raw files are never modified or deleted. The report counts the
groups and the final-version check (`--release`) refuses a dataset that contains them, until a
policy is decided (for example, keep one file per group and record the other as a duplicate of it).
That policy is an open decision; the duplicates are not removed automatically.

## 7. Limits of this experiment

- One authority was used. A second one (for example World Flora Online or POWO) would turn
  "GBIF disagrees" into "authorities disagree" and help with the family question.
- The check queries without authorship, which causes the ambiguity in cause B. Passing the
  authorship from the original label to GBIF would help for names that carry it (Flavia).
- Only 47 classes in two small datasets were tested. Pl@ntNet-300K has about a thousand
  species, so the share of outdated or ambiguous names must be measured again there.
- The result depends on the Backbone at the run date; the GBIF answers are cached in
  `datasets/_cache/gbif.json` (not versioned), and `gbif_report.csv` records the outcome.

## 8. Recommended next steps

1. Decide the five open entries (section 4) with the tutor or a botanist and update the
   mappings by hand.
2. Show the GBIF alternatives in the report when the match is at a higher rank, so cause B
   is visible without querying the API manually.
3. Send the authorship to GBIF when the original label has one.
4. Add a second authority and record disagreements as a separate status.
5. Record the run date and Backbone version in each report.

## 9. How to reproduce

```bash
python -m pytest                          # 101 tests, offline
python scripts/verify_mapping.py swedish_leaf
python scripts/verify_mapping.py flavia
```

The first command needs no network. The next two query GBIF and rewrite
`datasets/<name>/gbif_report.csv`; add `--apply` to update `status` and `note` in the
mapping file. The cache makes repeated runs offline.
