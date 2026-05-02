"""
Seed medical imaging library with curated open-access content.

Sources used:
  1. Wikimedia Commons — anatomy illustrations (CC-BY-SA / Public Domain)
  2. NIH OpenI — chest X-rays and radiology cases (Public Domain)
  3. Sketchfab — 3D anatomy models (CC-BY licenses)

Run:
  python -m scripts.seed_imaging          # from backend/ directory
  python -m scripts.seed_imaging --openi  # also fetch live from NIH OpenI API
"""
import asyncio
import sys
import uuid
import httpx

CURATED_IMAGES = [
    # ── CHEST X-RAY ──────────────────────────────────────────────────────────
    {
        "title": "Normal PA Chest Radiograph",
        "description": "Postero-anterior (PA) chest X-ray showing normal cardiac silhouette, clear lung fields, and normal bony thorax. The trachea is midline and the costophrenic angles are sharp.",
        "modality": "xray",
        "anatomy_region": "chest",
        "specialty": "radiology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/Chest_Xray_PA_3-8-2010.png/800px-Chest_Xray_PA_3-8-2010.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/Chest_Xray_PA_3-8-2010.png/400px-Chest_Xray_PA_3-8-2010.png",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Chest_Xray_PA_3-8-2010.png",
        "license": "CC-BY-SA 3.0",
        "attribution": "Stillwaterising / Wikimedia Commons / CC-BY-SA 3.0",
        "tags": ["chest", "xray", "normal", "PA view", "lung fields"],
    },
    {
        "title": "Left Lower Lobe Pneumonia",
        "description": "PA chest radiograph demonstrating left lower lobe consolidation consistent with lobar pneumonia. Note the loss of the left heart border (silhouette sign) and increased density overlying the lower left hemithorax.",
        "modality": "xray",
        "anatomy_region": "chest",
        "specialty": "radiology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Pneumonia_x-ray.jpg/800px-Pneumonia_x-ray.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Pneumonia_x-ray.jpg/400px-Pneumonia_x-ray.jpg",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Pneumonia_x-ray.jpg",
        "license": "CC-BY-SA 3.0",
        "attribution": "James Heilman, MD / Wikimedia Commons / CC-BY-SA 3.0",
        "tags": ["pneumonia", "consolidation", "chest", "xray", "infection", "silhouette sign"],
    },
    {
        "title": "Pleural Effusion — PA Chest X-ray",
        "description": "Chest radiograph showing a large right-sided pleural effusion with blunting of the right costophrenic angle and opacification of the lower right lung zone.",
        "modality": "xray",
        "anatomy_region": "chest",
        "specialty": "radiology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Pleural_effusion.jpg/800px-Pleural_effusion.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Pleural_effusion.jpg/400px-Pleural_effusion.jpg",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Pleural_effusion.jpg",
        "license": "CC-BY-SA 3.0",
        "attribution": "James Heilman, MD / Wikimedia Commons / CC-BY-SA 3.0",
        "tags": ["pleural effusion", "chest", "xray", "fluid"],
    },
    {
        "title": "Pneumothorax — Right-Sided",
        "description": "Chest X-ray demonstrating a right-sided pneumothorax with visible lung edge and absent lung markings peripheral to it.",
        "modality": "xray",
        "anatomy_region": "chest",
        "specialty": "radiology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/Pneumothorax_on_chest_xray_-_annotated.jpg/800px-Pneumothorax_on_chest_xray_-_annotated.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/Pneumothorax_on_chest_xray_-_annotated.jpg/400px-Pneumothorax_on_chest_xray_-_annotated.jpg",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Pneumothorax_on_chest_xray_-_annotated.jpg",
        "license": "CC-BY-SA 3.0",
        "attribution": "James Heilman, MD / Wikimedia Commons / CC-BY-SA 3.0",
        "tags": ["pneumothorax", "chest", "xray", "emergency", "air"],
    },
    # ── BRAIN MRI ─────────────────────────────────────────────────────────────
    {
        "title": "Normal Brain MRI — Axial T1",
        "description": "T1-weighted MRI of the brain at the level of the basal ganglia. The gray-white matter differentiation is well preserved. Ventricles are normal in size. No mass lesion or midline shift.",
        "modality": "mri",
        "anatomy_region": "brain",
        "specialty": "neurology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/Brain_MRI_107.jpg/800px-Brain_MRI_107.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/Brain_MRI_107.jpg/400px-Brain_MRI_107.jpg",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Brain_MRI_107.jpg",
        "license": "Public Domain",
        "attribution": "Taken from the NIH / Wikimedia Commons / Public Domain",
        "tags": ["brain", "mri", "T1", "normal", "neurology", "axial"],
    },
    {
        "title": "Ischemic Stroke — DWI MRI",
        "description": "Diffusion-weighted imaging (DWI) showing restricted diffusion in the left middle cerebral artery territory indicating acute ischemic stroke. Bright signal on DWI with corresponding dark signal on ADC map.",
        "modality": "mri",
        "anatomy_region": "brain",
        "specialty": "neurology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/Ischemic_stroke_MRI.jpg/800px-Ischemic_stroke_MRI.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/Ischemic_stroke_MRI.jpg/400px-Ischemic_stroke_MRI.jpg",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Ischemic_stroke_MRI.jpg",
        "license": "CC-BY-SA 3.0",
        "attribution": "James Heilman, MD / Wikimedia Commons / CC-BY-SA 3.0",
        "tags": ["stroke", "ischemia", "brain", "mri", "DWI", "neurology", "MCA"],
    },
    # ── BRAIN CT ──────────────────────────────────────────────────────────────
    {
        "title": "Hemorrhagic Stroke — CT Brain",
        "description": "Non-contrast CT of the brain showing a hyperdense lesion in the right basal ganglia consistent with acute intracerebral hemorrhage. Mass effect with mild midline shift to the left.",
        "modality": "ct",
        "anatomy_region": "brain",
        "specialty": "neurology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/CT_brain_hemorrhage.jpg/800px-CT_brain_hemorrhage.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/CT_brain_hemorrhage.jpg/400px-CT_brain_hemorrhage.jpg",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:CT_brain_hemorrhage.jpg",
        "license": "CC-BY-SA 3.0",
        "attribution": "James Heilman, MD / Wikimedia Commons / CC-BY-SA 3.0",
        "tags": ["hemorrhage", "stroke", "brain", "CT", "neurology", "basal ganglia", "emergency"],
    },
    # ── ABDOMINAL CT ──────────────────────────────────────────────────────────
    {
        "title": "Normal Abdominal CT — Axial",
        "description": "Axial contrast-enhanced CT of the abdomen at the level of the kidneys. Normal liver, spleen, pancreas, and bilateral kidneys are identified. No free fluid or lymphadenopathy.",
        "modality": "ct",
        "anatomy_region": "abdomen",
        "specialty": "radiology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/CT_abdomen.jpg/800px-CT_abdomen.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/CT_abdomen.jpg/400px-CT_abdomen.jpg",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:CT_abdomen.jpg",
        "license": "CC-BY-SA 3.0",
        "attribution": "Wikimedia Commons / CC-BY-SA 3.0",
        "tags": ["abdomen", "CT", "normal", "radiology", "axial"],
    },
    # ── CARDIAC ───────────────────────────────────────────────────────────────
    {
        "title": "Echocardiogram — Normal LV Function",
        "description": "Parasternal long axis view of the heart on transthoracic echocardiography showing normal left ventricular size and systolic function. The mitral and aortic valves are normal in appearance.",
        "modality": "ultrasound",
        "anatomy_region": "heart",
        "specialty": "cardiology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Phonocardiogram.png/800px-Phonocardiogram.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Phonocardiogram.png/400px-Phonocardiogram.png",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Phonocardiogram.png",
        "license": "Public Domain",
        "attribution": "Wikimedia Commons / Public Domain",
        "tags": ["heart", "ultrasound", "echo", "cardiology", "LV", "normal"],
    },
    # ── ANATOMY ILLUSTRATIONS ─────────────────────────────────────────────────
    {
        "title": "Human Heart — Anterior View",
        "description": "Detailed illustration of the human heart from an anterior perspective showing the major vessels, chambers, and coronary arteries. The right and left ventricles, atria, aorta, pulmonary trunk, superior and inferior vena cava are labeled.",
        "modality": "anatomy",
        "anatomy_region": "heart",
        "specialty": "cardiology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/Heart_diagram-en.svg/800px-Heart_diagram-en.svg.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/Heart_diagram-en.svg/400px-Heart_diagram-en.svg.png",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Heart_diagram-en.svg",
        "license": "CC-BY-SA 3.0",
        "attribution": "Wapcaplet / Wikimedia Commons / CC-BY-SA 3.0",
        "tags": ["heart", "anatomy", "cardiology", "chambers", "coronary", "diagram"],
    },
    {
        "title": "Human Brain — Lateral View",
        "description": "Lateral view of the human brain with labeled gyri, sulci, and major lobes. The frontal, parietal, temporal, and occipital lobes are clearly delineated. The cerebellum and brainstem are visible.",
        "modality": "anatomy",
        "anatomy_region": "brain",
        "specialty": "neurology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Lobes_of_the_brain_NL.svg/800px-Lobes_of_the_brain_NL.svg.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Lobes_of_the_brain_NL.svg/400px-Lobes_of_the_brain_NL.svg.png",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Lobes_of_the_brain_NL.svg",
        "license": "Public Domain",
        "attribution": "Patrick J. Lynch / Wikimedia Commons / Public Domain",
        "tags": ["brain", "anatomy", "neurology", "lobes", "cerebral cortex", "gyri"],
    },
    {
        "title": "Respiratory System Anatomy",
        "description": "Diagram of the human respiratory system including the nasal cavity, pharynx, larynx, trachea, bronchi, and lungs with labeled lobes. Alveolar detail shown in inset.",
        "modality": "anatomy",
        "anatomy_region": "chest",
        "specialty": "respiratory",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9f/Respiratory_system_complete_en.svg/800px-Respiratory_system_complete_en.svg.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9f/Respiratory_system_complete_en.svg/400px-Respiratory_system_complete_en.svg.png",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Respiratory_system_complete_en.svg",
        "license": "Public Domain",
        "attribution": "Wikimedia Commons / Public Domain",
        "tags": ["lungs", "respiratory", "anatomy", "trachea", "bronchi", "alveoli"],
    },
    {
        "title": "Kidney Cross-Section Anatomy",
        "description": "Coronal cross-section of the human kidney showing the cortex, medulla, renal pyramids, minor and major calyces, renal pelvis, and ureter. The blood supply via the renal artery and vein is illustrated.",
        "modality": "anatomy",
        "anatomy_region": "abdomen",
        "specialty": "nephrology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Blausen_0592_KidneyAnatomy_01.png/800px-Blausen_0592_KidneyAnatomy_01.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Blausen_0592_KidneyAnatomy_01.png/400px-Blausen_0592_KidneyAnatomy_01.png",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Blausen_0592_KidneyAnatomy_01.png",
        "license": "CC-BY 3.0",
        "attribution": "BruceBlaus / Wikimedia Commons / CC-BY 3.0",
        "tags": ["kidney", "anatomy", "nephrology", "cross-section", "renal cortex", "medulla"],
    },
    {
        "title": "Liver Anatomy — Segments",
        "description": "Couinaud segmental anatomy of the liver showing 8 functional segments with blood supply and biliary drainage. Essential for understanding liver surgery and imaging.",
        "modality": "anatomy",
        "anatomy_region": "abdomen",
        "specialty": "gastroenterology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Couinaud_classification_of_liver_segments.svg/800px-Couinaud_classification_of_liver_segments.svg.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Couinaud_classification_of_liver_segments.svg/400px-Couinaud_classification_of_liver_segments.svg.png",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Couinaud_classification_of_liver_segments.svg",
        "license": "Public Domain",
        "attribution": "Wikimedia Commons / Public Domain",
        "tags": ["liver", "anatomy", "Couinaud", "segments", "surgery", "gastroenterology"],
    },
    {
        "title": "Spinal Column — Lateral View",
        "description": "Lateral view of the vertebral column showing the cervical, thoracic, lumbar, sacral, and coccygeal regions with labeled vertebral bodies. The normal lordotic and kyphotic curvatures are illustrated.",
        "modality": "anatomy",
        "anatomy_region": "spine",
        "specialty": "orthopedics",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Gray_111_-_Vertebral_column-coloured.png/600px-Gray_111_-_Vertebral_column-coloured.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Gray_111_-_Vertebral_column-coloured.png/300px-Gray_111_-_Vertebral_column-coloured.png",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Gray_111_-_Vertebral_column-coloured.png",
        "license": "Public Domain",
        "attribution": "Gray's Anatomy / Wikimedia Commons / Public Domain",
        "tags": ["spine", "vertebral column", "anatomy", "cervical", "lumbar", "orthopedics"],
    },
    {
        "title": "Knee Joint — Sagittal MRI",
        "description": "Sagittal T2-weighted MRI of the knee joint demonstrating the anterior and posterior cruciate ligaments, medial and lateral menisci, patellar tendon, and articular cartilage surfaces.",
        "modality": "mri",
        "anatomy_region": "musculoskeletal",
        "specialty": "orthopedics",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/MRI_of_knee.jpg/800px-MRI_of_knee.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/MRI_of_knee.jpg/400px-MRI_of_knee.jpg",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:MRI_of_knee.jpg",
        "license": "CC-BY-SA 3.0",
        "attribution": "Hellerhoff / Wikimedia Commons / CC-BY-SA 3.0",
        "tags": ["knee", "MRI", "meniscus", "ACL", "orthopedics", "musculoskeletal"],
    },
    {
        "title": "Bone Fracture — Colles Fracture X-ray",
        "description": "PA and lateral wrist radiographs demonstrating a distal radial fracture (Colles fracture) with dorsal angulation and radial shortening. The classic dinner fork deformity is produced.",
        "modality": "xray",
        "anatomy_region": "musculoskeletal",
        "specialty": "orthopedics",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Collesfracture.png/800px-Collesfracture.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Collesfracture.png/400px-Collesfracture.png",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Collesfracture.png",
        "license": "Public Domain",
        "attribution": "Wikimedia Commons / Public Domain",
        "tags": ["fracture", "Colles", "wrist", "radius", "xray", "orthopedics", "trauma"],
    },
    {
        "title": "Histology — Normal Cardiac Muscle",
        "description": "H&E stain of cardiac muscle demonstrating branching striated muscle fibers with centrally located nuclei and intercalated discs. Magnification ×400.",
        "modality": "histology",
        "anatomy_region": "heart",
        "specialty": "pathology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/Cardiac_muscle_layer_of_the_heart.jpg/800px-Cardiac_muscle_layer_of_the_heart.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/Cardiac_muscle_layer_of_the_heart.jpg/400px-Cardiac_muscle_layer_of_the_heart.jpg",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Cardiac_muscle_layer_of_the_heart.jpg",
        "license": "CC-BY-SA 3.0",
        "attribution": "Olek Remesz / Wikimedia Commons / CC-BY-SA 3.0",
        "tags": ["histology", "cardiac muscle", "H&E", "pathology", "microscopy", "intercalated disc"],
    },
    {
        "title": "Histology — Normal Liver (H&E)",
        "description": "H&E stained section of normal liver parenchyma showing hepatocytes arranged in cords around a central vein. Portal tracts with bile ducts, hepatic arterioles, and portal venules are visible at the periphery.",
        "modality": "histology",
        "anatomy_region": "abdomen",
        "specialty": "pathology",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Normal_liver.jpg/800px-Normal_liver.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Normal_liver.jpg/400px-Normal_liver.jpg",
        "source_name": "Wikimedia Commons",
        "source_url": "https://commons.wikimedia.org/wiki/File:Normal_liver.jpg",
        "license": "Public Domain",
        "attribution": "Wikimedia Commons / Public Domain",
        "tags": ["histology", "liver", "hepatocytes", "H&E", "pathology", "portal tract"],
    },
]

# Sketchfab 3D anatomy models — all CC-BY licensed
ANATOMY_VIEWERS = [
    {
        "title": "Human Heart — 3D Interactive",
        "description": "Detailed 3D model of the human heart with labeled chambers, valves, and major vessels. Rotate, zoom, and explore the cardiac anatomy from any angle.",
        "organ_system": "cardiovascular",
        "anatomy_region": "heart",
        "embed_type": "sketchfab",
        "embed_id": "572827b523484334834e3c26e24f1fe8",
        "embed_url": "https://sketchfab.com/models/572827b523484334834e3c26e24f1fe8/embed?autospin=1&autostart=1",
        "thumbnail_url": "https://media.sketchfab.com/models/572827b523484334834e3c26e24f1fe8/thumbnails/6a8fcb24b6bc4d6f89ef5b61c1a4c62f/200x200.jpeg",
        "source_name": "Sketchfab",
        "source_url": "https://sketchfab.com/3d-models/572827b523484334834e3c26e24f1fe8",
        "license": "CC-BY 4.0",
        "attribution": "Sketchfab / CC-BY 4.0",
        "sort_order": 1,
    },
    {
        "title": "Human Brain — 3D Interactive",
        "description": "Complete 3D model of the human brain with gyri, sulci, cerebellum, brainstem, and internal structures. Ideal for neuroscience and clinical anatomy study.",
        "organ_system": "nervous",
        "anatomy_region": "brain",
        "embed_type": "sketchfab",
        "embed_id": "d3a4cc09e9fc4146b3b2b6ef9c00df1b",
        "embed_url": "https://sketchfab.com/models/d3a4cc09e9fc4146b3b2b6ef9c00df1b/embed?autospin=1&autostart=1",
        "thumbnail_url": "https://media.sketchfab.com/models/d3a4cc09e9fc4146b3b2b6ef9c00df1b/thumbnails/200x200.jpeg",
        "source_name": "Sketchfab",
        "source_url": "https://sketchfab.com/3d-models/d3a4cc09e9fc4146b3b2b6ef9c00df1b",
        "license": "CC-BY 4.0",
        "attribution": "Sketchfab / CC-BY 4.0",
        "sort_order": 2,
    },
    {
        "title": "Human Skull — 3D Interactive",
        "description": "Detailed human skull model with labeled bones, foramina, and sutures. Explore the cranium, mandible, and facial bones from all angles.",
        "organ_system": "musculoskeletal",
        "anatomy_region": "head",
        "embed_type": "sketchfab",
        "embed_id": "a5da2034b3754a91bdb59bbd0bc3c875",
        "embed_url": "https://sketchfab.com/models/a5da2034b3754a91bdb59bbd0bc3c875/embed?autospin=1&autostart=1",
        "thumbnail_url": "https://media.sketchfab.com/models/a5da2034b3754a91bdb59bbd0bc3c875/thumbnails/200x200.jpeg",
        "source_name": "Sketchfab",
        "source_url": "https://sketchfab.com/3d-models/a5da2034b3754a91bdb59bbd0bc3c875",
        "license": "CC-BY 4.0",
        "attribution": "Sketchfab / CC-BY 4.0",
        "sort_order": 3,
    },
    {
        "title": "Lungs & Respiratory Tree — 3D",
        "description": "3D model of the lungs with bronchial tree, showing the lobar and segmental anatomy essential for thoracic surgery and pulmonology.",
        "organ_system": "respiratory",
        "anatomy_region": "chest",
        "embed_type": "sketchfab",
        "embed_id": "e23d27f0dca34e6f9f61a4b1e7e0c524",
        "embed_url": "https://sketchfab.com/models/e23d27f0dca34e6f9f61a4b1e7e0c524/embed?autospin=1&autostart=1",
        "thumbnail_url": "https://media.sketchfab.com/models/e23d27f0dca34e6f9f61a4b1e7e0c524/thumbnails/200x200.jpeg",
        "source_name": "Sketchfab",
        "source_url": "https://sketchfab.com/3d-models/e23d27f0dca34e6f9f61a4b1e7e0c524",
        "license": "CC-BY 4.0",
        "attribution": "Sketchfab / CC-BY 4.0",
        "sort_order": 4,
    },
    {
        "title": "Knee Joint Anatomy — 3D",
        "description": "Complete 3D model of the knee joint including the femur, tibia, fibula, patella, cruciate ligaments, collateral ligaments, and menisci.",
        "organ_system": "musculoskeletal",
        "anatomy_region": "musculoskeletal",
        "embed_type": "sketchfab",
        "embed_id": "f0f55cceac884d5b83f3c55bb62a9ccf",
        "embed_url": "https://sketchfab.com/models/f0f55cceac884d5b83f3c55bb62a9ccf/embed?autospin=1&autostart=1",
        "thumbnail_url": "https://media.sketchfab.com/models/f0f55cceac884d5b83f3c55bb62a9ccf/thumbnails/200x200.jpeg",
        "source_name": "Sketchfab",
        "source_url": "https://sketchfab.com/3d-models/f0f55cceac884d5b83f3c55bb62a9ccf",
        "license": "CC-BY 4.0",
        "attribution": "Sketchfab / CC-BY 4.0",
        "sort_order": 5,
    },
    {
        "title": "Digestive System — 3D Overview",
        "description": "3D model of the gastrointestinal tract from esophagus to rectum, including the liver, gallbladder, pancreas, and spleen.",
        "organ_system": "digestive",
        "anatomy_region": "abdomen",
        "embed_type": "sketchfab",
        "embed_id": "1cd62e2d265845f8a9af38cbce80f7f0",
        "embed_url": "https://sketchfab.com/models/1cd62e2d265845f8a9af38cbce80f7f0/embed?autospin=1&autostart=1",
        "thumbnail_url": "https://media.sketchfab.com/models/1cd62e2d265845f8a9af38cbce80f7f0/thumbnails/200x200.jpeg",
        "source_name": "Sketchfab",
        "source_url": "https://sketchfab.com/3d-models/1cd62e2d265845f8a9af38cbce80f7f0",
        "license": "CC-BY 4.0",
        "attribution": "Sketchfab / CC-BY 4.0",
        "sort_order": 6,
    },
    {
        "title": "Vertebral Column — 3D",
        "description": "Complete spinal column with intervertebral discs and labeled vertebral regions. Explore cervical, thoracic, lumbar, sacral anatomy in 3D.",
        "organ_system": "musculoskeletal",
        "anatomy_region": "spine",
        "embed_type": "sketchfab",
        "embed_id": "3ca56b25e3784ca2818fc6d85befd39f",
        "embed_url": "https://sketchfab.com/models/3ca56b25e3784ca2818fc6d85befd39f/embed?autospin=1&autostart=1",
        "thumbnail_url": "https://media.sketchfab.com/models/3ca56b25e3784ca2818fc6d85befd39f/thumbnails/200x200.jpeg",
        "source_name": "Sketchfab",
        "source_url": "https://sketchfab.com/3d-models/3ca56b25e3784ca2818fc6d85befd39f",
        "license": "CC-BY 4.0",
        "attribution": "Sketchfab / CC-BY 4.0",
        "sort_order": 7,
    },
    {
        "title": "Kidney & Urinary Tract — 3D",
        "description": "3D model of the kidneys, ureters, bladder, and urethra with internal architecture showing cortex, medulla, and collecting system.",
        "organ_system": "urinary",
        "anatomy_region": "abdomen",
        "embed_type": "sketchfab",
        "embed_id": "a2cd8e8e1f3d4e8d9a3c5a2f8d1c7e4b",
        "embed_url": "https://sketchfab.com/models/a2cd8e8e1f3d4e8d9a3c5a2f8d1c7e4b/embed?autospin=1&autostart=1",
        "thumbnail_url": "https://media.sketchfab.com/models/a2cd8e8e1f3d4e8d9a3c5a2f8d1c7e4b/thumbnails/200x200.jpeg",
        "source_name": "Sketchfab",
        "source_url": "https://sketchfab.com/3d-models/a2cd8e8e1f3d4e8d9a3c5a2f8d1c7e4b",
        "license": "CC-BY 4.0",
        "attribution": "Sketchfab / CC-BY 4.0",
        "sort_order": 8,
    },
]


async def seed(fetch_openi: bool = False) -> None:
    """Seed the imaging library. Skips if data already exists."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    from app.core.database import engine, Base
    from app.models.models import MedicalImage, AnatomyViewer
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # Check if already seeded
        existing = await session.execute(select(MedicalImage).limit(1))
        if existing.scalar_one_or_none():
            print("Medical images already seeded — skipping curated images.")
        else:
            print(f"Seeding {len(CURATED_IMAGES)} curated images...")
            for item in CURATED_IMAGES:
                img = MedicalImage(id=uuid.uuid4(), **item)
                session.add(img)
            await session.commit()
            print("Curated images seeded.")

        # Anatomy viewers
        existing_v = await session.execute(select(AnatomyViewer).limit(1))
        if existing_v.scalar_one_or_none():
            print("Anatomy viewers already seeded — skipping.")
        else:
            print(f"Seeding {len(ANATOMY_VIEWERS)} anatomy viewers...")
            for item in ANATOMY_VIEWERS:
                v = AnatomyViewer(id=uuid.uuid4(), **item)
                session.add(v)
            await session.commit()
            print("Anatomy viewers seeded.")

        # Optionally fetch live from NIH OpenI
        if fetch_openi:
            await _fetch_openi(session)


async def _fetch_openi(session) -> None:
    """Fetch a batch of chest X-ray cases from NIH OpenI and add to DB."""
    from app.models.models import MedicalImage
    from sqlalchemy import select

    queries = [
        ("pneumonia", "xray", "chest"),
        ("pleural effusion", "xray", "chest"),
        ("chest normal", "xray", "chest"),
        ("brain mri", "mri", "brain"),
        ("lung cancer", "ct", "chest"),
    ]
    total_added = 0
    async with httpx.AsyncClient(timeout=15.0) as client:
        for q, modality, region in queries:
            try:
                resp = await client.get(
                    "https://openi.nlm.nih.gov/api/search",
                    params={"q": q, "m": 1, "n": 10, "it": "x,ct,mri"},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"  OpenI query '{q}' failed: {e}")
                continue

            for entry in data.get("list", []):
                uid = entry.get("uid", "")
                if not uid:
                    continue
                # Check not already in DB
                exists = await session.execute(
                    select(MedicalImage).where(MedicalImage.source_url.like(f"%{uid}%"))
                )
                if exists.scalar_one_or_none():
                    continue
                img_url = f"https://openi.nlm.nih.gov/imgs/512/{uid}.png"
                thumb_url = f"https://openi.nlm.nih.gov/imgs/128/{uid}.png"
                caption = entry.get("caption", "")
                title = entry.get("title") or caption[:80] or f"NIH OpenI — {uid}"
                img = MedicalImage(
                    id=uuid.uuid4(),
                    title=title[:300],
                    description=caption[:2000] if caption else None,
                    modality=modality,
                    anatomy_region=region,
                    specialty="radiology",
                    image_url=img_url,
                    thumbnail_url=thumb_url,
                    source_name="NIH OpenI",
                    source_url=f"https://openi.nlm.nih.gov/detailedresult?img={uid}",
                    license="Public Domain",
                    attribution="National Library of Medicine — NIH OpenI (Public Domain)",
                    tags=[q, modality, region],
                )
                session.add(img)
                total_added += 1

            await session.commit()
            print(f"  OpenI '{q}': added entries from batch.")

    print(f"NIH OpenI seed complete — {total_added} new images added.")


if __name__ == "__main__":
    fetch_openi = "--openi" in sys.argv
    asyncio.run(seed(fetch_openi=fetch_openi))
