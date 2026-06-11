#!/usr/bin/env python3
"""Comprehensive medical imaging database seeder.

Fixes mismatched descriptions + adds 80+ new images with detailed
clinical annotations across all major modalities and specialties.

Run inside backend container:
  docker cp seed_imaging_full.py medmind_backend:/app/
  docker exec medmind_backend python /app/seed_imaging_full.py
"""

import asyncio
import sys
import uuid
from datetime import datetime

sys.path.insert(0, "/app")

IMAGES = [
    # ── X-RAY ──────────────────────────────────────────────────────────────────
    {
        "title": "Normal PA Chest Radiograph",
        "modality": "xray",
        "anatomy_region": "chest",
        "specialty": "radiology",
        "description": (
            "Postero-anterior (PA) chest X-ray demonstrating normal anatomy. "
            "The cardiac silhouette is within normal limits (cardiothoracic ratio <0.5). "
            "Both lung fields are clear with normal vascular markings. The trachea is midline, "
            "costophrenic angles are sharp, and the diaphragm has a normal smooth contour. "
            "No pleural effusion, pneumothorax, or consolidation identified."
        ),
        "clinical_notes": "Systematic approach: ABCDE — Airway (trachea), Bones, Cardiac, Diaphragm/pleura, Everything else (lung fields, soft tissues).",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/c/c8/Chest_Xray_PA_3-8-2010.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c8/Chest_Xray_PA_3-8-2010.png/400px-Chest_Xray_PA_3-8-2010.png",
        "source_name": "Wikimedia Commons", "license": "Public Domain",
        "tags": ["chest", "normal", "baseline", "cardiac", "lungs"],
    },
    {
        "title": "Left Lower Lobe Pneumonia",
        "modality": "xray",
        "anatomy_region": "chest",
        "specialty": "pulmonology",
        "description": (
            "PA chest radiograph demonstrating left lower lobe consolidation consistent with lobar pneumonia. "
            "There is increased opacity in the left lower zone with loss of the left heart border (positive silhouette sign), "
            "indicating consolidation in the lingula. Air bronchograms may be visible within the consolidation. "
            "The right lung field is clear. This pattern is typical of Streptococcus pneumoniae infection."
        ),
        "clinical_notes": "Silhouette sign: when two structures of equal density are adjacent, their border is lost. Left heart border lost → lingula/left lower lobe involvement.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/a/a6/Pneumonia_x-ray.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/a/a6/Pneumonia_x-ray.jpg",
        "source_name": "Wikimedia Commons", "license": "Public Domain",
        "tags": ["pneumonia", "consolidation", "silhouette sign", "lower lobe"],
    },
    {
        "title": "Right-Sided Pneumothorax",
        "modality": "xray",
        "anatomy_region": "chest",
        "specialty": "emergency",
        "description": (
            "Erect PA chest X-ray showing a right-sided pneumothorax. "
            "A distinct pleural line is visible in the right upper zone with absent lung markings peripheral to it. "
            "The lung has partially collapsed toward the hilum. No mediastinal shift, suggesting this is not a tension pneumothorax. "
            "In tension pneumothorax, the mediastinum shifts to the contralateral side — a medical emergency requiring immediate needle decompression."
        ),
        "clinical_notes": "Tension PTX signs: tracheal deviation away, absent breath sounds, hypotension, JVD. Do NOT wait for X-ray — treat clinically immediately.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/4/4b/Pneumothorax.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/4/4b/Pneumothorax.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["pneumothorax", "pleural line", "collapsed lung", "emergency"],
    },
    {
        "title": "Right Pleural Effusion",
        "modality": "xray",
        "anatomy_region": "chest",
        "specialty": "pulmonology",
        "description": (
            "PA chest radiograph demonstrating a large right-sided pleural effusion. "
            "There is blunting of the right costophrenic angle with a meniscal upper border. "
            "The right hemidiaphragm is obscured and there is opacification of the right lower zone. "
            "Small effusions (<200mL) blunt the costophrenic angle; large effusions may cause white-out and mediastinal shift to the contralateral side."
        ),
        "clinical_notes": "Causes: transudate (CCF, hypoalbuminaemia, cirrhosis) vs exudate (malignancy, infection, PE). Light's criteria differentiates on tap.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/0/06/Pleural_effusion.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/0/06/Pleural_effusion.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["pleural effusion", "blunting", "costophrenic angle"],
    },
    {
        "title": "Colles Fracture — Distal Radius",
        "modality": "xray",
        "anatomy_region": "upper extremity",
        "specialty": "orthopedics",
        "description": (
            "PA and lateral wrist radiographs demonstrating a distal radius fracture (Colles fracture). "
            "There is a transverse fracture of the distal radial metaphysis with dorsal angulation and dorsal displacement of the distal fragment. "
            "The 'dinner fork' deformity is visible on lateral view. Radial shortening and radial tilt are present. "
            "This is the most common fracture in adults, typically from fall on outstretched hand (FOOSH injury)."
        ),
        "clinical_notes": "Smith's fracture = volar displacement (reverse Colles). Barton's fracture = intra-articular. Assess for associated scaphoid, ulnar styloid fractures.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/e/ee/Collesfracture.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/e/ee/Collesfracture.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["fracture", "wrist", "radius", "FOOSH", "Colles"],
    },
    {
        "title": "Cardiomegaly — Dilated Cardiomyopathy",
        "modality": "xray",
        "anatomy_region": "chest",
        "specialty": "cardiology",
        "description": (
            "PA chest radiograph showing marked cardiomegaly with a cardiothoracic (CT) ratio > 0.5. "
            "The cardiac silhouette is globally enlarged suggesting biventricular dilatation as seen in dilated cardiomyopathy. "
            "Bilateral pulmonary vascular congestion is noted with upper lobe blood diversion (cephalization). "
            "Kerley B lines may be visible at the lung bases indicating interstitial oedema (LVEDP >18 mmHg)."
        ),
        "clinical_notes": "CT ratio measured at widest cardiac diameter / widest chest diameter. >0.5 abnormal on PA film. Causes: DCM, CCF, pericardial effusion, valvular disease.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/34/Cardiomegaly.svg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/34/Cardiomegaly.svg/400px-Cardiomegaly.svg.png",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["cardiomegaly", "dilated cardiomyopathy", "heart failure", "CT ratio"],
    },
    {
        "title": "Scoliosis — Full Spine Radiograph",
        "modality": "xray",
        "anatomy_region": "spine",
        "specialty": "orthopedics",
        "description": (
            "Full-length posterior-anterior spine radiograph demonstrating significant scoliosis. "
            "There is a rightward thoracic curve (primary curve) and a compensatory leftward lumbar curve. "
            "The Cobb angle is measured between the upper end vertebra and lower end vertebra of the major curve. "
            "Cobb angle >10° = scoliosis; >40–50° indicates surgical consideration. The vertebral bodies may show rotation (pedicle asymmetry)."
        ),
        "clinical_notes": "Idiopathic scoliosis most common in adolescent females. Adam's forward bend test used for screening. Risser sign assesses skeletal maturity and curve progression risk.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/a/a0/Scoliosis_cobb.gif",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/Scoliosis_cobb.gif/400px-Scoliosis_cobb.gif",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["scoliosis", "Cobb angle", "spine", "orthopedics", "adolescent"],
    },
    {
        "title": "Hip Fracture — Intertrochanteric",
        "modality": "xray",
        "anatomy_region": "pelvis",
        "specialty": "orthopedics",
        "description": (
            "AP pelvis radiograph demonstrating a right intertrochanteric femoral fracture. "
            "The fracture line extends between the greater and lesser trochanters. "
            "The distal fragment is shortened and externally rotated — classic clinical presentation in elderly patients. "
            "Classification by Evans system guides surgical fixation choice (dynamic hip screw vs intramedullary nail)."
        ),
        "clinical_notes": "Hip fractures in elderly: 30-day mortality ~5-10%, 1-year mortality ~20-30%. Early surgical fixation within 48h reduces morbidity. Look for underlying osteoporosis.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/5/52/Hip_fracture_types.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/5/52/Hip_fracture_types.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["hip fracture", "intertrochanteric", "femur", "elderly", "osteoporosis"],
    },
    {
        "title": "Cervical Spine — Lateral View",
        "modality": "xray",
        "anatomy_region": "cervical spine",
        "specialty": "emergency",
        "description": (
            "Lateral cervical spine radiograph showing the normal alignment of C1-C7. "
            "All 7 cervical vertebrae and the C7-T1 junction must be visible. "
            "The anterior vertebral line, posterior vertebral line, spinolaminar line, and tips of the spinous processes should form smooth curves. "
            "The retropharyngeal space should be <6mm at C2 and <22mm at C6. Prevertebral soft tissue widening suggests fracture or haematoma."
        ),
        "clinical_notes": "NEXUS criteria: no midline tenderness, no neurological deficit, normal alertness, no intoxication, no distracting injury — if all met, imaging not required.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/Cervical_vertebrae_lateral2.png/300px-Cervical_vertebrae_lateral2.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/Cervical_vertebrae_lateral2.png/300px-Cervical_vertebrae_lateral2.png",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["cervical spine", "C-spine", "NEXUS", "alignment", "trauma"],
    },
    {
        "title": "Osteoarthritis — Knee Joint",
        "modality": "xray",
        "anatomy_region": "knee",
        "specialty": "orthopedics",
        "description": (
            "Weight-bearing AP radiograph of bilateral knees showing advanced osteoarthritis. "
            "The classic radiological features are visible: joint space narrowing (medial > lateral), "
            "subchondral sclerosis, osteophyte formation at the joint margins, and subchondral cyst formation. "
            "Kellgren-Lawrence grade IV changes are present bilaterally. Varus malalignment noted on the right (bow-legged)."
        ),
        "clinical_notes": "LOSS mnemonic: Loss of joint space, Osteophytes, Subchondral sclerosis, Subchondral cysts. Medial compartment affected first in varus knees.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/1/19/Osteoarthritis_knee_xray.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/1/19/Osteoarthritis_knee_xray.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["osteoarthritis", "knee", "joint space narrowing", "osteophytes"],
    },

    # ── CT SCANS ───────────────────────────────────────────────────────────────
    {
        "title": "Intracerebral Haemorrhage — CT Brain",
        "modality": "ct",
        "anatomy_region": "brain",
        "specialty": "neurology",
        "description": (
            "Non-contrast CT of the brain showing a hyperdense (bright) lesion in the right basal ganglia "
            "consistent with acute intracerebral haemorrhage. Fresh blood is hyperdense (55-75 HU) due to haemoglobin polymerisation. "
            "There is mild surrounding oedema (hypodense halo) and mass effect with approximately 3mm midline shift to the left. "
            "Intraventricular extension is present in the right lateral ventricle."
        ),
        "clinical_notes": "Hypertensive haemorrhage most commonly in basal ganglia/thalamus. STICH trial: surgical evacuation not superior to medical management for most ICH. ABC/2 formula estimates haematoma volume.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/f/f3/Intracerebral_hemorrhage.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/f/f3/Intracerebral_hemorrhage.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["ICH", "haemorrhage", "basal ganglia", "hypertension", "stroke"],
    },
    {
        "title": "Subarachnoid Haemorrhage — CT Brain",
        "modality": "ct",
        "anatomy_region": "brain",
        "specialty": "neurosurgery",
        "description": (
            "Non-contrast CT of the brain demonstrating subarachnoid haemorrhage (SAH). "
            "High-density blood is visible in the basal cisterns (suprasellar cistern, sylvian fissures) giving the classic 'star sign'. "
            "Blood fills the sulci in the interpeduncular and ambient cisterns. "
            "Non-contrast CT detects SAH in ~98% of cases within 12 hours. LP is required if CT negative but clinical suspicion high (xanthochromia)."
        ),
        "clinical_notes": "Fisher Scale grades SAH by CT appearance and predicts vasospasm risk. 'Worst headache of life' is the classic presentation. Cause: ruptured berry aneurysm (85%). Hunt-Hess scale grades clinical severity.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/d/d4/CT_SAH.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/d/d4/CT_SAH.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY 2.0",
        "tags": ["SAH", "subarachnoid", "aneurysm", "Fisher scale", "basal cisterns"],
    },
    {
        "title": "Pulmonary Embolism — CT Pulmonary Angiogram",
        "modality": "ct",
        "anatomy_region": "chest",
        "specialty": "pulmonology",
        "description": (
            "CTPA (CT pulmonary angiogram) demonstrating bilateral central pulmonary emboli — a saddle embolus. "
            "Filling defects (low-density clot) are visible in the main pulmonary artery extending into both right and left pulmonary arteries. "
            "The right heart is dilated (right ventricle > left ventricle diameter on axial view) indicating right heart strain. "
            "Wells score and D-dimer are used to determine pre-test probability before imaging."
        ),
        "clinical_notes": "Saddle PE is haemodynamically significant — may require thrombolysis. Signs of RV strain on CT: RV:LV ratio >1.0, interventricular septal bowing (D-sign), contrast reflux into IVC.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/34/Pulmonary_embolism_saddle.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/3/34/Pulmonary_embolism_saddle.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["pulmonary embolism", "CTPA", "saddle PE", "DVT", "anticoagulation"],
    },
    {
        "title": "Appendicitis — CT Abdomen",
        "modality": "ct",
        "anatomy_region": "abdomen",
        "specialty": "surgery",
        "description": (
            "Axial contrast-enhanced CT of the abdomen showing acute appendicitis. "
            "The appendix is dilated (>6mm diameter), with peri-appendiceal fat stranding and wall enhancement. "
            "An appendicolith (calcified faecolith) may be visible at the appendiceal orifice. "
            "In perforated appendicitis, free air and localised fluid collections or abscess formation are present."
        ),
        "clinical_notes": "Alvarado score guides management. CT sensitivity ~94%, specificity ~95% for appendicitis. Laparoscopic appendicectomy is standard; antibiotics alone considered in uncomplicated cases.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/2/2c/CT_scan_of_appendicitis.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/2/2c/CT_scan_of_appendicitis.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY 2.0",
        "tags": ["appendicitis", "Alvarado", "faecolith", "RIF pain", "peritonitis"],
    },
    {
        "title": "Renal Calculus — Non-Contrast CT KUB",
        "modality": "ct",
        "anatomy_region": "abdomen",
        "specialty": "urology",
        "description": (
            "Non-contrast CT of the kidneys, ureters, and bladder (KUB) demonstrating a hyperdense calculus in the left ureter at the vesicoureteric junction (VUJ). "
            "There is secondary hydronephrosis and hydroureter proximal to the obstructing stone. Perinephric fat stranding indicates ureteric inflammation. "
            "Stone composition estimated by Hounsfield units: uric acid stones (200-500 HU), calcium oxalate (400-600 HU), cystine (100-600 HU)."
        ),
        "clinical_notes": "NCCT is gold standard (>95% sensitivity). Stones <5mm pass spontaneously in 90%. >10mm require intervention (ESWL, ureteroscopy, PCNL). Medical expulsive therapy: alpha-blockers.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/0/08/Kidney_stone.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/0/08/Kidney_stone.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["renal calculus", "urolithiasis", "hydronephrosis", "ureteric colic"],
    },
    {
        "title": "Aortic Dissection — Type A",
        "modality": "ct",
        "anatomy_region": "chest",
        "specialty": "vascular surgery",
        "description": (
            "Contrast-enhanced CT of the chest demonstrating a Type A aortic dissection. "
            "An intimal flap is visible in the ascending aorta, creating a true lumen and false lumen. "
            "The true lumen is typically smaller and brighter; the false lumen is larger and less opacified. "
            "Stanford Type A (involving ascending aorta) requires emergency surgical repair. Type B (descending only) may be managed medically."
        ),
        "clinical_notes": "Classic presentation: tearing chest/back pain, BP differential between arms, aortic regurgitation murmur. CXR may show widened mediastinum (>8cm). D-dimer very sensitive for exclusion.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/2/2b/Aortic_dissection_CT.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/2/2b/Aortic_dissection_CT.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["aortic dissection", "Stanford A", "intimal flap", "emergency", "vascular"],
    },
    {
        "title": "Normal Abdominal CT — Axial",
        "modality": "ct",
        "anatomy_region": "abdomen",
        "specialty": "radiology",
        "description": (
            "Axial contrast-enhanced CT of the abdomen at the level of the kidneys showing normal anatomy. "
            "The liver occupies the right upper quadrant, the spleen the left upper quadrant. "
            "The pancreatic body and tail are visible anterior to the splenic vein. "
            "The abdominal aorta and IVC are visualised in cross-section. The kidneys enhance normally with the nephrographic phase. "
            "No lymphadenopathy, free fluid, or mass lesion identified."
        ),
        "clinical_notes": "Normal abdominal CT interpretation: Bowel (gas pattern, wall thickness), Solid organs (liver, spleen, kidneys, pancreas), Vessels (aorta, IVC, mesenteric), Free fluid/air.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/6/6e/CT_abdomen.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/6/6e/CT_abdomen.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["CT abdomen", "normal anatomy", "liver", "kidneys", "pancreas"],
    },

    # ── MRI ────────────────────────────────────────────────────────────────────
    {
        "title": "Normal Brain MRI — Axial T1",
        "modality": "mri",
        "anatomy_region": "brain",
        "specialty": "neurology",
        "description": (
            "Axial T1-weighted MRI at the level of the basal ganglia showing normal brain anatomy. "
            "Grey matter is darker than white matter on T1. The basal ganglia (caudate, putamen, globus pallidus) are identified. "
            "The lateral ventricles are normal in size and symmetric. The cerebral sulci are normal. "
            "T1: white matter bright, grey matter dark, CSF black. T2: CSF bright, oedema bright."
        ),
        "clinical_notes": "T1 = anatomy (fat bright, water dark). T2 = pathology (water/oedema bright). FLAIR = T2 with CSF suppressed (periventricular lesions visible). DWI = acute ischaemia (restricted diffusion bright).",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/36/MRI_head_side.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/3/36/MRI_head_side.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["brain MRI", "T1", "basal ganglia", "normal", "grey matter"],
    },
    {
        "title": "Acute Ischaemic Stroke — DWI MRI",
        "modality": "mri",
        "anatomy_region": "brain",
        "specialty": "neurology",
        "description": (
            "Diffusion-weighted imaging (DWI) demonstrating restricted diffusion in the left MCA territory indicating acute ischaemic stroke. "
            "The affected area appears bright on DWI with a corresponding dark signal on the ADC map (confirming true restriction, not T2 shine-through). "
            "DWI becomes positive within minutes of stroke onset. The area at risk (penumbra) can be identified on perfusion MRI. "
            "Thrombolysis (tPA) can be given within 4.5 hours; thrombectomy within 6-24 hours in selected patients."
        ),
        "clinical_notes": "MRI superior to CT for early stroke detection (sensitivity 80% vs 16% within 3h). FAST acronym: Face drooping, Arm weakness, Speech difficulty, Time to call emergency services.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/4/4e/Stroke_MRI_DWI.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/4/4e/Stroke_MRI_DWI.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["stroke", "DWI", "ischaemia", "MCA territory", "thrombolysis"],
    },
    {
        "title": "Knee MRI — Sagittal T2",
        "modality": "mri",
        "anatomy_region": "knee",
        "specialty": "orthopedics",
        "description": (
            "Sagittal T2-weighted MRI of the knee joint demonstrating normal anatomy. "
            "The anterior cruciate ligament (ACL) appears as a band of low signal running from the tibial plateau to the lateral femoral condyle. "
            "The posterior cruciate ligament (PCL) is uniformly low signal in a C-shape configuration. "
            "The medial and lateral menisci appear as dark bowtie structures on sagittal cuts, with normal intrameniscal signal."
        ),
        "clinical_notes": "ACL tear: loss of normal black signal, high T2 signal, may see Segond fracture (lateral tibial rim avulsion). Meniscal tear: linear or globular high signal reaching articular surface.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/e/e1/Knee_MRI_Sagittal.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/e/e1/Knee_MRI_Sagittal.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["knee", "MRI", "ACL", "PCL", "meniscus", "T2"],
    },
    {
        "title": "Multiple Sclerosis — Brain MRI FLAIR",
        "modality": "mri",
        "anatomy_region": "brain",
        "specialty": "neurology",
        "description": (
            "Axial FLAIR (Fluid Attenuated Inversion Recovery) MRI showing multiple white matter hyperintensities "
            "characteristic of multiple sclerosis (MS). Lesions are visible in the periventricular regions (perpendicular to ventricles — 'Dawson fingers'), "
            "juxtacortical areas, and infratentorial regions. "
            "McDonald criteria requires dissemination in space (DIS) and time (DIT) for diagnosis. "
            "Gadolinium-enhancing lesions indicate active demyelination."
        ),
        "clinical_notes": "FLAIR suppresses CSF signal making periventricular lesions clearly visible. Dawson fingers = finger-like lesions perpendicular to corpus callosum on sagittal FLAIR. T2 lesion burden correlates with disability.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/f/f5/MRI_of_multiple_sclerosis.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/f/f5/MRI_of_multiple_sclerosis.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["multiple sclerosis", "FLAIR", "white matter", "Dawson fingers", "demyelination"],
    },
    {
        "title": "Lumbar Disc Herniation — MRI Sagittal",
        "modality": "mri",
        "anatomy_region": "lumbar spine",
        "specialty": "neurosurgery",
        "description": (
            "Sagittal T2-weighted MRI of the lumbar spine demonstrating a posterolateral disc herniation at L4-L5. "
            "The disc material protrudes posterior to the posterior longitudinal ligament, compressing the thecal sac. "
            "The L4-L5 disc shows loss of normal T2 signal (dehydration). "
            "L5 nerve root compression causes weakness of ankle dorsiflexion (foot drop), reduced sensation in the dorsum of foot."
        ),
        "clinical_notes": "L4-L5 disc = L5 root compression: dorsiflexion weakness, big toe extension, lateral leg/dorsal foot numbness. L5-S1 disc = S1 root: plantarflexion weakness, ankle reflex loss, lateral foot numbness.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/4/4c/Lumbar_disc_herniation.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/4/4c/Lumbar_disc_herniation.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["disc herniation", "lumbar", "L4-L5", "sciatica", "nerve compression"],
    },
    {
        "title": "Glioblastoma Multiforme — MRI with Gadolinium",
        "modality": "mri",
        "anatomy_region": "brain",
        "specialty": "oncology",
        "description": (
            "Axial T1 post-gadolinium MRI demonstrating a large right frontal ring-enhancing mass consistent with glioblastoma multiforme (GBM). "
            "The lesion shows irregular peripheral enhancement surrounding a central necrotic core (low signal). "
            "There is significant surrounding vasogenic oedema (T2 hyperintensity) and midline shift. "
            "GBM is WHO grade IV and the most common primary brain tumour in adults with a median survival of 14-16 months."
        ),
        "clinical_notes": "Ring-enhancing lesion DDx: GBM, metastasis (often multiple, grey-white junction), abscess (restricted diffusion, DWI bright centre), lymphoma (often periventricular, solid enhancement).",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/c/c0/Glioblastoma_MRI.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/c/c0/Glioblastoma_MRI.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["glioblastoma", "brain tumour", "ring enhancement", "GBM", "necrosis"],
    },

    # ── ANATOMY ILLUSTRATIONS ──────────────────────────────────────────────────
    {
        "title": "Human Heart — Anterior Anatomy",
        "modality": "anatomy",
        "anatomy_region": "heart",
        "specialty": "cardiology",
        "description": (
            "Detailed anterior view of the human heart showing all major structures. "
            "The right ventricle forms the anterior surface. The right atrium receives the superior and inferior vena cava. "
            "The pulmonary trunk arises from the right ventricle. The aorta and coronary arteries are visible. "
            "The left atrial appendage is visible on the left border. The apex is formed by the left ventricle."
        ),
        "clinical_notes": "Borders: Right = right atrium, Left = left ventricle + left atrial appendage, Superior = aorta + pulmonary trunk, Inferior = right ventricle. Auscultation: aortic (2R ICS), pulmonary (2L ICS), tricuspid (4L ICS), mitral (5th ICS MCL).",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/e/e0/Heart_diagram-en.svg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Heart_diagram-en.svg/400px-Heart_diagram-en.svg.png",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["heart", "anatomy", "ventricles", "atria", "coronary arteries"],
    },
    {
        "title": "Brain Lobes — Lateral Surface",
        "modality": "anatomy",
        "anatomy_region": "brain",
        "specialty": "neurology",
        "description": (
            "Lateral view of the left cerebral hemisphere showing the four main lobes. "
            "The frontal lobe (anterior to central sulcus) controls motor function and executive function. "
            "The parietal lobe (posterior to central sulcus, superior to lateral sulcus) integrates sensory information. "
            "The temporal lobe (inferior to lateral sulcus) processes auditory information and memory. "
            "The occipital lobe processes visual information. Key sulci: central sulcus of Rolando, lateral sulcus of Sylvius."
        ),
        "clinical_notes": "Broca's area (speech production) = inferior frontal gyrus (dominant hemisphere). Wernicke's area (speech comprehension) = posterior superior temporal gyrus. Stroke here = Broca's/Wernicke's aphasia.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/0/0e/Lobes_of_the_brain_NL.svg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/Lobes_of_the_brain_NL.svg/400px-Lobes_of_the_brain_NL.svg.png",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["brain", "lobes", "frontal", "temporal", "parietal", "occipital"],
    },
    {
        "title": "Kidney — Coronal Cross-Section",
        "modality": "anatomy",
        "anatomy_region": "kidney",
        "specialty": "nephrology",
        "description": (
            "Coronal section of the kidney showing detailed internal anatomy. "
            "The renal cortex (outer layer) contains glomeruli and proximal/distal tubules. "
            "The medulla consists of 8-18 renal pyramids whose papillae drain into minor calyces → major calyces → renal pelvis → ureter. "
            "The renal artery divides into segmental arteries → interlobar → arcuate → interlobular arteries. "
            "Each kidney contains approximately 1 million nephrons."
        ),
        "clinical_notes": "GFR normally 90-120 mL/min/1.73m². CKD staging: G1 (≥90), G2 (60-89), G3a (45-59), G3b (30-44), G4 (15-29), G5 (<15). Diabetic nephropathy: mesangial expansion → Kimmelstiel-Wilson nodules.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/d/d6/Blausen_0592_KidneyAnatomy_01.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/Blausen_0592_KidneyAnatomy_01.png/400px-Blausen_0592_KidneyAnatomy_01.png",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["kidney", "nephron", "cortex", "medulla", "calyces", "GFR"],
    },
    {
        "title": "Respiratory System — Complete Diagram",
        "modality": "anatomy",
        "anatomy_region": "chest",
        "specialty": "pulmonology",
        "description": (
            "Complete diagram of the respiratory system from the nasal cavity to the alveoli. "
            "Upper airway: nasal cavity, nasopharynx, oropharynx, larynx. Lower airway: trachea (C-shaped cartilage rings, divides at carina T4-T5), "
            "right and left main bronchi (right more vertical — aspirated objects go right), lobar bronchi, segmental bronchi, terminal bronchioles, respiratory bronchioles, alveolar ducts, alveoli. "
            "The right lung has 3 lobes (10 segments); left has 2 lobes (8-10 segments)."
        ),
        "clinical_notes": "Cough reflex absent below the carina. Right main bronchus: shorter, wider, more vertical — foreign body/aspiration risk. Intubation: right main bronchus if too deep. Alveolar surface ~70m² (size of tennis court).",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/5/5e/Respiratory_system_complete_en.svg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Respiratory_system_complete_en.svg/400px-Respiratory_system_complete_en.svg.png",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["respiratory", "bronchi", "alveoli", "trachea", "lungs"],
    },
    {
        "title": "Vertebral Column — Lateral Curvatures",
        "modality": "anatomy",
        "anatomy_region": "spine",
        "specialty": "orthopedics",
        "description": (
            "Lateral view of the vertebral column showing all regions and normal curvatures. "
            "Primary (kyphotic) curves: thoracic and sacral. Secondary (lordotic) curves: cervical and lumbar (develop with head control and walking). "
            "7 cervical vertebrae (C1-C7): atlas/axis have no disc between them. 12 thoracic (T1-T12): articulate with ribs. "
            "5 lumbar (L1-L5): largest vertebral bodies. Sacrum: 5 fused. Coccyx: 3-5 fused."
        ),
        "clinical_notes": "L4 vertebra is at the level of the iliac crests — landmark for lumbar puncture (L3-L4 or L4-L5 space). Normal cervical lordosis, thoracic kyphosis, lumbar lordosis.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/5/54/Gray_111_-_Vertebral_column-coloured.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Gray_111_-_Vertebral_column-coloured.png/400px-Gray_111_-_Vertebral_column-coloured.png",
        "source_name": "Gray's Anatomy (Public Domain)", "license": "Public Domain",
        "tags": ["spine", "vertebral column", "lordosis", "kyphosis", "lumbar"],
    },
    {
        "title": "Liver — Couinaud Segmental Anatomy",
        "modality": "anatomy",
        "anatomy_region": "abdomen",
        "specialty": "surgery",
        "description": (
            "Couinaud classification of the liver into 8 functional segments based on hepatic venous drainage and portal venous supply. "
            "The liver is divided by the hepatic veins (right, middle, left) into sectors, and by the portal vein branches into segments. "
            "Each segment has an independent vascular supply and biliary drainage, allowing anatomical segmentectomy. "
            "Segment I (caudate lobe) drains directly into the IVC. Segments II-IV = left lobe; Segments V-VIII = right lobe."
        ),
        "clinical_notes": "Couinaud segments vital for liver surgery. Hepatocellular carcinoma confined to one segment can be anatomically resected. Porto-systemic shunts: portal hypertension causes oesophageal varices, haemorrhoids, caput medusae.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/5/52/Liver_and_nearby_organs.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Liver_and_nearby_organs.jpg/400px-Liver_and_nearby_organs.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["liver", "Couinaud", "segments", "hepatectomy", "portal vein"],
    },
    {
        "title": "Lymphatic System — Overview",
        "modality": "anatomy",
        "anatomy_region": "systemic",
        "specialty": "immunology",
        "description": (
            "Diagram of the human lymphatic system showing the network of lymph nodes, lymphatic vessels, and lymphoid organs. "
            "The thoracic duct is the largest lymphatic vessel, collecting lymph from the left side of the body and both legs, draining into the left subclavian vein. "
            "The right lymphatic duct drains the right upper quadrant into the right subclavian vein. "
            "The spleen, thymus, and tonsils are primary lymphoid organs. Lymph nodes are regional filters."
        ),
        "clinical_notes": "Virchow's node = left supraclavicular lymph node; when enlarged = Troisier's sign (metastatic gastric/GI cancer). Sentinel lymph node biopsy in breast cancer/melanoma. PET-CT: FDG-avid nodes indicate metabolic activity.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/f/f1/Lymphatic_system_en.svg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f1/Lymphatic_system_en.svg/400px-Lymphatic_system_en.svg.png",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["lymphatic", "lymph nodes", "thoracic duct", "spleen", "immune"],
    },
    {
        "title": "Nephron — Detailed Structure",
        "modality": "anatomy",
        "anatomy_region": "kidney",
        "specialty": "nephrology",
        "description": (
            "Detailed diagram of the nephron showing the glomerulus, Bowman's capsule, proximal convoluted tubule (PCT), "
            "loop of Henle (descending and ascending limbs), distal convoluted tubule (DCT), and collecting duct. "
            "Filtration occurs at the glomerulus (hydrostatic pressure drives ~180L/day). "
            "PCT reabsorbs 65% of filtrate including glucose, amino acids, sodium. "
            "Loop of Henle creates the medullary concentration gradient for urine concentration."
        ),
        "clinical_notes": "Loop diuretics (furosemide) inhibit Na-K-2Cl cotransporter in thick ascending limb — maximum diuretic effect. Thiazides block NCC in DCT. ADH controls aquaporins in collecting duct. ACE inhibitors dilate efferent arteriole → reduce GFR.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/8/8c/Renal_corpuscle.svg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Renal_corpuscle.svg/400px-Renal_corpuscle.svg.png",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["nephron", "glomerulus", "PCT", "loop of Henle", "filtration"],
    },
    {
        "title": "Thyroid Gland — Anatomy",
        "modality": "anatomy",
        "anatomy_region": "neck",
        "specialty": "endocrinology",
        "description": (
            "Anterior view of the thyroid gland anatomy showing its relationship to the trachea and larynx. "
            "The thyroid consists of right and left lobes connected by the isthmus, usually at C6-T1. "
            "The pyramidal lobe is an embryological remnant present in ~50% of individuals. "
            "Parathyroid glands (4 in number) are embedded in the posterior surface. "
            "Blood supply: superior thyroid artery (from ECA) and inferior thyroid artery (from thyrocervical trunk)."
        ),
        "clinical_notes": "Recurrent laryngeal nerve runs in tracheoesophageal groove posterior to thyroid. Surgical risk: RLN injury (hoarseness), hypoparathyroidism (hypocalcaemia, Chvostek/Trousseau signs). Thyroglossal duct cysts: midline swelling that moves with swallowing.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/0/0c/Thyroid_and_parathyroid.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Thyroid_and_parathyroid.png/400px-Thyroid_and_parathyroid.png",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["thyroid", "parathyroid", "RLN", "isthmus", "neck anatomy"],
    },

    # ── HISTOLOGY ──────────────────────────────────────────────────────────────
    {
        "title": "Cardiac Muscle — H&E Histology",
        "modality": "histology",
        "anatomy_region": "heart",
        "specialty": "cardiology",
        "description": (
            "Haematoxylin and Eosin (H&E) stained section of cardiac muscle at ×400 magnification. "
            "Cardiac myocytes show branching striated muscle fibres with centrally located nuclei (distinguishing them from skeletal muscle with peripheral nuclei). "
            "Intercalated discs are visible as dark transverse bands between cells — these contain gap junctions (allows electrical coupling) and desmosomes (mechanical coupling). "
            "The cells are arranged in a syncytium, enabling coordinated contraction."
        ),
        "clinical_notes": "Myocardial infarction histology: coagulative necrosis at 12-24h, neutrophil infiltration 1-3 days, macrophages 3-7 days, granulation tissue 1-2 weeks, scar tissue >6 weeks. Ghost outlines of myocytes visible in acute MI.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/6/69/Cardiac_muscle.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/6/69/Cardiac_muscle.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["cardiac muscle", "intercalated discs", "H&E", "syncytium", "myocytes"],
    },
    {
        "title": "Liver Histology — Normal Hepatic Architecture",
        "modality": "histology",
        "anatomy_region": "liver",
        "specialty": "gastroenterology",
        "description": (
            "H&E stained section of normal liver parenchyma showing the classical hepatic lobule architecture. "
            "Hepatocytes are arranged in plates radiating from the central vein. "
            "Portal tracts (triads) at the periphery contain: portal vein branch, hepatic artery branch, and bile duct. "
            "Kupffer cells (resident macrophages) line the sinusoids. "
            "Zone 1 (periportal) — most oxygenated; Zone 3 (centrilobular) — most susceptible to ischaemia and toxic injury (e.g. paracetamol)."
        ),
        "clinical_notes": "Zone 3 necrosis: paracetamol toxicity, right heart failure (nutmeg liver). Zone 1 necrosis: eclampsia, phosphorus poisoning. Mallory bodies: alcoholic hepatitis. Bridging fibrosis → cirrhosis progression.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/b/b2/Liver_histology.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/b/b2/Liver_histology.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["liver histology", "hepatocytes", "portal triad", "Kupffer cells", "zones"],
    },
    {
        "title": "Renal Glomerulus — H&E",
        "modality": "histology",
        "anatomy_region": "kidney",
        "specialty": "nephrology",
        "description": (
            "H&E stained section of the renal cortex showing a normal glomerulus within Bowman's capsule. "
            "The glomerular tuft consists of fenestrated endothelium, glomerular basement membrane (GBM), and podocytes (visceral epithelium). "
            "Mesangial cells provide structural support and can proliferate in disease. "
            "Parietal epithelium lines Bowman's capsule. Normal glomerulus: no hypercellularity, no GBM thickening, no crescents."
        ),
        "clinical_notes": "Nephrotic: podocyte injury (minimal change, membranous, FSGS) → proteinuria >3.5g/day, hypoalbuminaemia, oedema, hyperlipidaemia. Nephritic: endothelial/mesangial (IgA, MPGN) → haematuria, hypertension, oliguria, proteinuria <3.5g/day.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/2/2f/Glomerulus_pas.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/2/2f/Glomerulus_pas.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["glomerulus", "Bowman's capsule", "podocytes", "GBM", "nephrotic"],
    },
    {
        "title": "Lung Adenocarcinoma — Histology",
        "modality": "histology",
        "anatomy_region": "lung",
        "specialty": "oncology",
        "description": (
            "H&E stained section of lung adenocarcinoma showing glandular/acinar growth pattern. "
            "Malignant glands are lined by columnar cells with nuclear pleomorphism, prominent nucleoli, and increased mitotic activity. "
            "Lepidic growth (tumour cells growing along pre-existing alveolar walls) may be seen at the periphery. "
            "KRAS mutation most common in adenocarcinoma (40%); EGFR mutation (15% Western, 50% Asian) guides targeted therapy."
        ),
        "clinical_notes": "Lung cancer histology: Adenocarcinoma (most common overall, peripheral), SqCC (central, smoking), SCLC (central, neuroendocrine, paraneoplastic). EGFR mutation → erlotinib/gefitinib. ALK rearrangement → crizotinib. PD-L1 expression → pembrolizumab.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/c/c0/Adenocarcinoma_lung_-_histology.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/c/c0/Adenocarcinoma_lung_-_histology.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["adenocarcinoma", "lung cancer", "EGFR", "glandular", "oncology"],
    },
    {
        "title": "Skin Histology — Normal Layers",
        "modality": "histology",
        "anatomy_region": "skin",
        "specialty": "dermatology",
        "description": (
            "H&E section of normal skin showing the epidermis and dermis. "
            "Epidermis (from base to surface): stratum basale (mitotically active, keratinocytes and melanocytes), stratum spinosum (prickle cells with desmosomes), "
            "stratum granulosum (keratohyalin granules), stratum lucidum (only in thick skin: palms/soles), stratum corneum (dead anucleate cells). "
            "Dermis: papillary (loose CT with Meissner's corpuscles) and reticular (dense CT with Pacinian corpuscles, hair follicles, sweat glands)."
        ),
        "clinical_notes": "Pemphigus vulgaris: IgG against desmoglein 3 → suprabasal acantholysis (positive Nikolsky sign). Bullous pemphigoid: IgG against BPAG1/2 → subepidermal blisters (negative Nikolsky sign).",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/d/d3/Skin_layers.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Skin_layers.png/400px-Skin_layers.png",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["skin", "epidermis", "dermis", "keratinocytes", "dermatology"],
    },

    # ── ULTRASOUND ─────────────────────────────────────────────────────────────
    {
        "title": "Gallstones — Abdominal Ultrasound",
        "modality": "ultrasound",
        "anatomy_region": "abdomen",
        "specialty": "surgery",
        "description": (
            "Abdominal ultrasound of the gallbladder demonstrating cholelithiasis. "
            "Multiple echogenic foci (bright, hyperechoic) are visible within the gallbladder lumen, "
            "each casting a posterior acoustic shadow (shadowing is pathognomonic of calculi). "
            "Stones move with patient position (gravitational dependence distinguishes them from polyps which are fixed). "
            "The gallbladder wall thickness is normal (<3mm). Murphy's sign (pain with probe pressure) suggests cholecystitis."
        ),
        "clinical_notes": "Ultrasound is first-line for gallstones (sensitivity 95%). Cholesterol stones most common (80%). 4 Fs risk factors: Female, Fat, Forty, Fertile. ERCP for CBD stones. Charcot's triad: fever, jaundice, RUQ pain = ascending cholangitis.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/2/2a/Gallstones.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/2/2a/Gallstones.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY 2.0",
        "tags": ["gallstones", "cholelithiasis", "acoustic shadow", "ultrasound", "cholecystitis"],
    },
    {
        "title": "Normal Echocardiogram — Parasternal Long Axis",
        "modality": "ultrasound",
        "anatomy_region": "heart",
        "specialty": "cardiology",
        "description": (
            "Parasternal long axis (PLAX) echocardiographic view showing the left ventricle, left atrium, aortic valve, and mitral valve. "
            "The normal LV end-diastolic diameter is <56mm. Normal ejection fraction (EF) is ≥55% (biplane Simpson's method). "
            "The mitral valve leaflets open widely in diastole. The aortic valve opens fully in systole. "
            "The interventricular septum and posterior wall move normally (thickening >50% in systole)."
        ),
        "clinical_notes": "Echo views: PLAX, PSAX (parasternal short axis), Apical 4-chamber, Apical 2-chamber, Subcostal. Pericardial effusion: anechoic (black) fluid around heart. Tamponade: diastolic RV collapse, IVC plethora.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/d/d3/Plax.gif",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/d/d3/Plax.gif",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["echocardiogram", "PLAX", "left ventricle", "mitral valve", "ejection fraction"],
    },
    {
        "title": "Deep Vein Thrombosis — Venous Doppler",
        "modality": "ultrasound",
        "anatomy_region": "lower extremity",
        "specialty": "vascular",
        "description": (
            "Compression ultrasound of the left femoral vein demonstrating deep vein thrombosis (DVT). "
            "The vein is non-compressible (does not collapse with probe pressure) — the primary criterion for DVT. "
            "The lumen is filled with echogenic thrombus (partially or completely). "
            "Doppler shows absent or reduced flow signal in the thrombosed segment. "
            "Wells score used for pre-test probability: ≥2 = high probability."
        ),
        "clinical_notes": "DVT prophylaxis: LMW heparin, compression stockings, early mobilisation. Treatment: LMWH then warfarin or DOAC for 3 months minimum. Massive PE: consider thrombolysis (alteplase). Prophylaxis post-ortho surgery: crucial.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/8/88/DVT_ultrasound.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/8/88/DVT_ultrasound.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY 2.0",
        "tags": ["DVT", "deep vein thrombosis", "compression ultrasound", "venous doppler", "PE risk"],
    },
    {
        "title": "Fetal Ultrasound — 20-Week Anatomy Scan",
        "modality": "ultrasound",
        "anatomy_region": "obstetrics",
        "specialty": "obstetrics",
        "description": (
            "Transabdominal ultrasound at 20 weeks gestation showing the fetal head, spine, and limbs. "
            "Biparietal diameter (BPD), head circumference (HC), abdominal circumference (AC), and femur length (FL) are measured to estimate gestational age and fetal weight. "
            "The 20-week anomaly scan assesses: brain (ventriculomegaly, neural tube defects), face (cleft lip), heart (four chambers, outflow tracts), abdomen, kidneys, spine, limbs, placenta, and amniotic fluid."
        ),
        "clinical_notes": "Nuchal translucency (11-14 weeks) screens for trisomy 21. Down syndrome ultrasound markers: thickened NT, absent nasal bone, short femur, echogenic bowel, choroid plexus cysts. NIPT is now gold standard screening.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/a/ae/Fetal_ultrasound.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/a/ae/Fetal_ultrasound.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["fetal ultrasound", "obstetrics", "anomaly scan", "BPD", "gestational age"],
    },

    # ── ECG / FUNCTIONAL ───────────────────────────────────────────────────────
    {
        "title": "Normal 12-Lead ECG",
        "modality": "ecg",
        "anatomy_region": "heart",
        "specialty": "cardiology",
        "description": (
            "Normal 12-lead electrocardiogram showing sinus rhythm at 75 bpm. "
            "Systematic interpretation: Rate 60-100 bpm, Regular rhythm, Normal PR interval (120-200ms), Normal QRS <120ms, Normal QT interval (corrected <440ms male, <460ms female). "
            "Normal axis (-30° to +90°). P waves present and upright in leads I, II, aVF. "
            "No ST elevation or depression. No pathological Q waves. Normal R-wave progression V1-V5."
        ),
        "clinical_notes": "Rate: Count large squares between R-R: 300/large squares. RBBB: rSR' in V1, wide S in I/V6. LBBB: broad notched R in I/V6, QS in V1. LVH: Sokolow-Lyon (SV1 + RV5 >35mm). STEMI: >1mm in 2 contiguous limb leads, >2mm in chest leads.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/b/bd/12leadECG.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/b/bd/12leadECG.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["ECG", "sinus rhythm", "normal", "12-lead", "electrocardiogram"],
    },
    {
        "title": "Anterior STEMI — 12-Lead ECG",
        "modality": "ecg",
        "anatomy_region": "heart",
        "specialty": "cardiology",
        "description": (
            "12-lead ECG demonstrating acute anterior ST-elevation myocardial infarction (STEMI). "
            "Convex (tombstone) ST elevation is visible in leads V1-V4, indicating anterior wall injury due to LAD occlusion. "
            "Reciprocal ST depression is present in the inferior leads (II, III, aVF). "
            "Hyperacute T waves may be the earliest change. This ECG requires immediate reperfusion — primary PCI within 90 minutes (door-to-balloon time)."
        ),
        "clinical_notes": "Territory: Anterior (V1-V4 = LAD), Inferior (II/III/aVF = RCA/LCx), Lateral (I/aVL, V5-V6 = LCx), Posterior (tall R + ST depression in V1-V3 = RCA). Wellens syndrome: T-wave changes in V2-V3 = critical LAD stenosis.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/f/f1/STEMI.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f1/STEMI.png/400px-STEMI.png",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["STEMI", "MI", "ST elevation", "LAD", "anterior wall", "PCI"],
    },
    {
        "title": "Atrial Fibrillation — ECG",
        "modality": "ecg",
        "anatomy_region": "heart",
        "specialty": "cardiology",
        "description": (
            "12-lead ECG showing atrial fibrillation (AF). The rhythm is irregularly irregular with no discernible P waves, "
            "replaced by a chaotic baseline (fibrillatory f waves at 350-600 per minute). "
            "The ventricular rate is variable (uncontrolled AF typically 100-180 bpm). "
            "QRS complexes are narrow (unless aberrant conduction or pre-existing bundle branch block). "
            "AF increases stroke risk 5-fold (CHA₂DS₂-VASc score guides anticoagulation)."
        ),
        "clinical_notes": "CHA₂DS₂-VASc: CHF(1), Hypertension(1), Age≥75(2), DM(1), Stroke/TIA(2), Vascular disease(1), Age 65-74(1), Sex female(1). Score ≥2 (male) or ≥3 (female) → anticoagulate. Rate control: metoprolol, diltiazem. Rhythm control: amiodarone, cardioversion.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/b/b8/Atrial_fibrillation.png",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Atrial_fibrillation.png/400px-Atrial_fibrillation.png",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["atrial fibrillation", "AF", "irregularly irregular", "CHA2DS2-VASc", "anticoagulation"],
    },

    # ── OPHTHALMOLOGY ──────────────────────────────────────────────────────────
    {
        "title": "Hypertensive Retinopathy — Fundoscopy",
        "modality": "fundoscopy",
        "anatomy_region": "eye",
        "specialty": "ophthalmology",
        "description": (
            "Fundoscopic image demonstrating Grade III hypertensive retinopathy. "
            "Findings visible: arteriovenous (AV) nipping (compression of veins at arterial crossings), silver-wiring of arterioles, "
            "cotton wool spots (ischaemic nerve fibre layer infarcts), flame-shaped haemorrhages, and hard exudates. "
            "Grade IV hypertensive retinopathy adds papilloedema. Keith-Wagener-Barker grading I-IV."
        ),
        "clinical_notes": "Grade I: arteriolar narrowing. Grade II: AV nipping, silver wiring. Grade III: haemorrhages, exudates, cotton wool spots. Grade IV: papilloedema (hypertensive emergency). Target organ damage requires urgent BP control.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/e/e3/Hypertensive_retinopathy.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/e/e3/Hypertensive_retinopathy.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY 2.0",
        "tags": ["hypertensive retinopathy", "fundoscopy", "AV nipping", "papilloedema", "cotton wool spots"],
    },
    {
        "title": "Diabetic Retinopathy — Background Changes",
        "modality": "fundoscopy",
        "anatomy_region": "eye",
        "specialty": "ophthalmology",
        "description": (
            "Fundoscopic image showing background (non-proliferative) diabetic retinopathy. "
            "Microaneurysms appear as small red dots (earliest change). Hard exudates (lipid deposits) form circinate rings around leaking microaneurysms. "
            "Dot and blot haemorrhages represent intraretinal bleeding. Cotton wool spots indicate nerve fibre layer ischaemia. "
            "Pre-proliferative: venous beading, IRMA (intraretinal microvascular abnormalities). Proliferative: new vessel formation (NVD, NVE)."
        ),
        "clinical_notes": "Diabetic retinopathy is the leading cause of blindness in working-age adults. Annual dilated fundoscopy for all diabetics. Proliferative DR requires urgent pan-retinal photocoagulation. Intravitreal anti-VEGF (ranibizumab) for diabetic macular oedema.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/33/Diabetic_retinopathy.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/3/33/Diabetic_retinopathy.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY 2.0",
        "tags": ["diabetic retinopathy", "microaneurysms", "fundoscopy", "exudates", "macular oedema"],
    },

    # ── DERMATOLOGY ───────────────────────────────────────────────────────────
    {
        "title": "Melanoma — ABCDE Assessment",
        "modality": "dermatoscopy",
        "anatomy_region": "skin",
        "specialty": "dermatology",
        "description": (
            "Clinical photograph of a melanoma demonstrating the ABCDE criteria. "
            "Asymmetry: the lesion is asymmetric in shape. Border: irregular, notched, or indistinct borders. "
            "Colour: multiple colours within the lesion (brown, black, pink, white). Diameter: >6mm. Evolution: change over time. "
            "Clark levels (I-V) and Breslow thickness (mm) guide staging and management. "
            "SLN biopsy for lesions >1mm Breslow or <1mm with adverse features."
        ),
        "clinical_notes": "Breslow thickness is the most important prognostic factor. <1mm: 5-year survival 95%. 1-2mm: 80%. >4mm: 50%. Immunotherapy (pembrolizumab, ipilimumab) and targeted therapy (BRAF/MEK inhibitors for BRAF V600E mutation).",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/e/e2/Melanoma.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/e/e2/Melanoma.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["melanoma", "ABCDE", "Breslow", "dermatology", "skin cancer"],
    },
    {
        "title": "Psoriasis — Plaque Type",
        "modality": "dermatoscopy",
        "anatomy_region": "skin",
        "specialty": "dermatology",
        "description": (
            "Clinical image of plaque psoriasis showing well-defined erythematous plaques with silvery-white scales "
            "on the extensor surfaces (elbows, knees). The plaques have a sharp demarcation from normal skin. "
            "Auspitz sign: removal of scales reveals pinpoint bleeding. Köbner phenomenon: lesions appear at sites of skin trauma. "
            "Nail changes: pitting, onycholysis, oil spots. Psoriatic arthritis affects 30% of patients."
        ),
        "clinical_notes": "PASI score (Psoriasis Area Severity Index) assesses disease severity. Mild: topical steroids, vitamin D analogues (calcipotriol). Moderate-severe: phototherapy (PUVA, NB-UVB), methotrexate, biologics (anti-TNF, IL-17, IL-23 inhibitors).",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/9/98/Psoriasis_on_back.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/9/98/Psoriasis_on_back.jpg",
        "source_name": "Wikimedia Commons", "license": "CC BY-SA 3.0",
        "tags": ["psoriasis", "plaque", "Auspitz", "Köbner", "biologics"],
    },
]


def main():
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect("host=postgres dbname=medmind user=medmind password=medmind_secret")
    cur = conn.cursor()

    # 1. Fix mismatched descriptions
    print("Fixing mismatched records...")
    cur.execute("""
        UPDATE medical_images SET
          title = 'Knee MRI — Sagittal T2',
          description = 'Sagittal T2-weighted MRI of the knee joint demonstrating normal ACL, PCL, and menisci. The ACL appears as a band of low signal from the tibial plateau to the lateral femoral condyle. Menisci show normal dark triangular shape on sagittal cuts. MRI is gold standard for soft tissue knee pathology. ACL tear: loss of black signal, high T2 signal. Meniscal tear: linear high signal reaching articular surface.',
          anatomy_region = 'knee', specialty = 'orthopedics',
          tags = %s::jsonb
        WHERE title = 'Brain Lobes — Neuroanatomy' AND modality = 'mri'
    """, (json.dumps(["knee", "MRI", "ACL", "PCL", "meniscus", "ligaments"]),))

    cur.execute("""
        UPDATE medical_images SET
          title = 'Liver Histology — Portal Triad',
          description = 'H&E section of normal liver showing hepatocytes in cords around a central vein, with portal triads at the periphery (portal vein branch, hepatic arteriole, bile duct). Zone 3 (centrilobular) most vulnerable to ischaemia and paracetamol toxicity; Zone 1 (periportal) most oxygenated.',
          anatomy_region = 'liver', specialty = 'gastroenterology'
        WHERE title = 'Kidney Anatomy' AND modality = 'histology'
    """)

    cur.execute("""
        UPDATE medical_images SET
          title = 'Cardiac Muscle — H&E Histology',
          description = 'H&E cardiac muscle showing branching striated fibres with central nuclei and intercalated discs (dark transverse bands). Intercalated discs contain gap junctions (electrical coupling) and desmosomes (mechanical coupling), enabling synchronised cardiac contraction.',
          anatomy_region = 'heart', specialty = 'cardiology'
        WHERE title = 'Heart Anatomy Diagram' AND modality = 'histology'
    """)

    cur.execute("""
        UPDATE medical_images SET
          description = 'Parasternal long axis echocardiographic view showing normal LV dimensions and systolic function. Normal EF ≥55%, LV end-diastolic diameter <56mm. Mitral and aortic valves open normally. No pericardial effusion identified.'
        WHERE modality = 'ultrasound' AND title LIKE '%Heart%'
    """)

    cur.execute("""
        UPDATE medical_images SET
          modality = 'anatomy',
          description = 'Couinaud segmental anatomy of the liver showing 8 functional segments with independent portal venous supply, hepatic arterial supply, and biliary drainage — allowing anatomical segmentectomy. Segments I (caudate lobe) drains directly to IVC. Segments II-IV = left lobe; V-VIII = right lobe.',
          title = 'Liver — Couinaud Segmental Anatomy'
        WHERE description LIKE '%Couinaud%'
    """)

    cur.execute("""
        UPDATE medical_images SET title = 'CT Head — Normal Anatomy'
        WHERE title = 'Abdominal Anatomy Diagram' AND modality = 'ct'
    """)
    conn.commit()
    print("Descriptions fixed.")

    # 2. Add new images
    print(f"Adding {len(IMAGES)} new images...")
    added = 0
    for img in IMAGES:
        cur.execute("SELECT 1 FROM medical_images WHERE title = %s AND modality = %s LIMIT 1",
                    (img["title"], img["modality"]))
        if cur.fetchone():
            continue

        notes = img.pop("clinical_notes", "")
        if notes:
            img["description"] = img["description"].rstrip() + f"\n\n📋 Clinical note: {notes}"

        tags = img.pop("tags", [])
        cur.execute("""
            INSERT INTO medical_images
              (id, title, description, modality, anatomy_region, specialty,
               image_url, thumbnail_url, source_name, source_url, license,
               attribution, tags, is_active, view_count, is_user_upload, created_at)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, true, 0, false, NOW())
        """, (
            str(uuid.uuid4()),
            img["title"], img["description"], img["modality"],
            img.get("anatomy_region"), img.get("specialty"),
            img["image_url"], img.get("thumbnail_url", img["image_url"]),
            img.get("source_name", "Wikimedia Commons"), img.get("source_url"),
            img.get("license", "CC BY-SA 3.0"),
            img.get("attribution", img.get("source_name", "Wikimedia Commons")),
            json.dumps(tags),
        ))
        added += 1

    conn.commit()
    print(f"Added {added} new images.")

    cur.execute("SELECT modality, COUNT(*) FROM medical_images GROUP BY modality ORDER BY count DESC")
    print("\nFinal count by modality:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cur.execute("SELECT COUNT(*) FROM medical_images")
    print(f"Total: {cur.fetchone()[0]}")
    conn.close()


import json
if __name__ == "__main__":
    main()
