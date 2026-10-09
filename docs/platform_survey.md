# Platform Architecture Survey 

This document defines the proposed technical architecture for implementing a **single, centralized web platform**. The system will integrate image uploads, AI model inference, user management, and dataset administration into a unified application.

## 1. Unified Platform Workflow

To avoid fragmenting the system across multiple tools, the web platform will support the main stages of the data lifecycle through four consecutive steps:

```text
[ User (Mobile/Desktop) ] ──(Upload Image)──► [ Python Backend ] ──► [ Cloudflare R2 Storage ]
                                                      │
                                               (Run Model)
                                                      │
[ Admin Panel (Review) ] ◄──(Save ID)─────────┴──────────────────► [ PostgreSQL Database ]
```

1. **Image Capture and Upload:** Users access the web platform from a desktop or mobile device and upload a leaf photograph. The system automatically removes EXIF metadata to protect privacy before storing the image.
2. **Real-Time Prediction:** The backend processes the image and passes it to the *Deep Learning* model loaded in memory. The system returns a hierarchical classification consisting of Family → Genus → Species.
3. **Efficient Storage:** The image file is uploaded to cloud object storage, while its storage reference and prediction results are recorded in the database.
4. **Validation (Citizen Science and Administration):** Through a private administration panel integrated into the same web application, administrators review predictions and correct labels when necessary. This allows the platform to provide its own basic annotation and review functionality.

## 2. Proposed Solution Components

To build a single web application without relying on external annotation tools, I chose the following core technologies.

### 2.1. Backend and Administration Panel: Django (Python)

* **Rationale:** Django provides built-in user authentication, permission management, and an administration interface available at `/admin`.
* **Advantage:** It reduces the amount of functionality that must be developed from scratch and avoids the need to integrate external tools such as Label Studio or CVAT for basic review tasks.

### 2.2. Database: PostgreSQL

* **Rationale:** PostgreSQL stores structured information about users, plant taxonomy records obtained from sources such as GBIF, and image prediction histories.
* **Advantage:** It supports structured queries, relationships between families, genera, and species, and traceability of corrections made by administrators.

### 2.3. Image Storage: Cloudflare R2

* **Rationale:** Storing tens of gigabytes of leaf photographs, as may be required for datasets comparable in scale to Pl@ntNet-300K, can be impractical on a conventional application server.
* **Advantage:** Cloudflare R2 provides S3-compatible object storage without egress fees.
* **Application:** It enables the platform to centralize original photographs and newly uploaded images, making them easier to retrieve and prepare for future training datasets.

### 2.4. Frontend: HTML5 + Tailwind CSS + HTMX

* **Rationale:** This combination supports the development of a lightweight, modern interface that adapts to mobile devices.
* **Advantage:** HTMX enables dynamic updates to parts of a web page without requiring a separate frontend application.
* **Application:** The interface will support image uploads from a device's gallery or camera. If a more native app-like experience is required, the platform can be extended into a Progressive Web App (PWA).

---

## 3. Comparison of Alternative Technologies

If any architectural component needs to be replaced because of development time, performance, or maintenance constraints, the following alternatives can be considered.

| Component / Layer             | Primary Choice                          | Alternative Considered | Reason for Exclusion from the Initial Architecture                                                                                                                                                                                |
| :---------------------------- | :-------------------------------------- | :--------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Backend Development**       | **Django**                              | FastAPI                | FastAPI is well suited to inference services but does not provide a built-in administration panel equivalent to Django's. User management and data administration would need to be implemented or integrated separately.          |
| **Annotation and Review**     | **Django Admin Panel**                  | Label Studio / CVAT    | These tools provide advanced annotation capabilities but introduce additional infrastructure and integration requirements. An integrated solution is preferred for the project's basic review needs.                              |
| **S3-Compatible Storage**     | **Cloudflare R2**                       | Self-hosted MinIO      | MinIO requires infrastructure provisioning, storage management, and ongoing maintenance. R2 reduces operational overhead by providing a managed storage service.                                                                  |
| **Final Dataset Publication** | **Own Database and Storage**            | Hugging Face / Zenodo  | These platforms are considered potential options for publishing and distributing the final dataset once the project is completed.                                                                                                 |
| **Species Identification**    | **Custom Model Running in the Backend** | Pl@ntNet API           | A custom model provides greater control over inference and allows the development of a neural network tailored to the academic objective. An external API introduces third-party dependencies, usage limits, and potential costs. |

---

## 4. Architectural Overview and Expected Outcome

The proposed solution is a **single, integrated web platform** built around Django as the application core, PostgreSQL for structured data, Cloudflare R2 for image storage, and a responsive web interface.

The architecture will support the following functionalities:

* User, permission, and role management.
* Leaf photograph upload and storage.
* Removal of sensitive EXIF metadata.
* Execution of the tree species classification model.
* Storage of prediction results and confidence scores.
* Management of the taxonomy of families, genera, and species.
* Manual review and correction of classification results at first.
* Preservation of validated labels for preparing future training datasets.
* Export of the data required to train and evaluate new models.

This architecture keeps the main functionalities within a single application while separating the database, image storage, and inference logic. This separation improves maintainability and allows individual components to evolve independently.
